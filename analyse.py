import json
import threading
import time
from datetime import datetime
from typing import Optional

from solana.rpc.api import Client
from solana.rpc.commitment import Finalized
from solders.solders import Pubkey


def rpc_client():
    client = Client("https://api.mainnet-beta.solana.com")
    if client.is_connected():
        print("client success")
        return client
    else:
        print("client fail")


def get_meta(client: Client, smart_wallet: str):
    signatures = client.get_signatures_for_address(account=Pubkey.from_string(smart_wallet),
                                                   limit=10,
                                                   commitment=Finalized).value
    if not signatures:
        return None

    latest_signature = signatures[0].signature
    transaction = json.loads(client.get_transaction(latest_signature,max_supported_transaction_version=0).to_json())
    if transaction and transaction['result']['meta']['err'] is None:
        return transaction['result']['blockTime'],transaction['result']['meta'],latest_signature
    return None,None



def analyze_transaction_direction(
        wallet_address:str,
        meta: dict,
        quote_token_mint: str = "So11111111111111111111111111111111111111112"  # 默认用 SOL 作为报价币
) -> Optional[str]:
    """
    分析交易方向（买入/卖出）

    :param tx_data: get_transaction 返回的原始数据
    :param target_token_mint: 目标代币的 mint 地址（如 RAY）
    :param quote_token_mint: 报价代币的 mint 地址（默认为 SOL）
    :return: "buy", "sell" 或 None（无法判断）
    """
    try:
        if not meta or meta.get("err"):
            return None
        # print(json.dumps(meta))
        # 解析代币余额变化
        token_address,token_balance_change = _get_token_balance_change(wallet_address,meta)

        # 解析报价币变化（SOL 或 USDC 等）
        if quote_token_mint == "SOL":
            quote_change = _get_sol_balance_change(meta)
        else:
            token_address,quote_change = _get_token_balance_change(wallet_address,meta)

        # 判断方向
        if token_balance_change > 0 and quote_change < 0:
            sol_num = "{:.2f}".format(abs(quote_change)/1000000000)
            return "买入: "+str(sol_num) +"SOL "+ token_address
        elif token_balance_change < 0 and quote_change > 0:
            sol_num = "{:.2f}".format(abs(quote_change)/1000000000)
            return "卖出: "+str(sol_num) +"SOL "+ token_address

        # 复杂情况：通过日志进一步分析
        log_messages = meta.get("logMessages", [])
        return _analyze_from_logs(log_messages)

    except Exception as e:
        print(f"分析失败: {str(e)}")
        return None

def _get_token_balance_change(wallet_address:str,meta: dict):
    """获取代币余额变化"""

    def find_balance(balances):
        for item in balances:
            owner_address = item.get("owner")
            if owner_address==wallet_address:
                token_address=item.get('mint')
                ui_token_amount = item.get("uiTokenAmount", {})
                amount_str = ui_token_amount.get("amount", "0")
                return token_address,int(amount_str)

        return "",0

    token_address1,pre = find_balance(meta.get("preTokenBalances", []))
    token_address2,post = find_balance(meta.get("postTokenBalances", []))

    if token_address1 == "":
        token_address = token_address2
    elif token_address2 == "":
        token_address = token_address1
    else:
        token_address = token_address1

    return token_address,post - pre

def _get_sol_balance_change(meta: dict) -> int:
    """获取 SOL 余额变化"""
    if not meta.get("preBalances") or not meta.get("postBalances"):
        return 0
    #  交易前各账户的余额
    pre_sol = meta["preBalances"][0]
    #  交易后各账户的余额
    post_sol = meta["postBalances"][0]
    return post_sol - pre_sol

def _analyze_from_logs(logs: list) -> Optional[str]:
    """从日志中分析交易方向"""
    for msg in logs:
        msg_lower = msg.lower()
        if "swap" in msg_lower:
            if any(kw in msg_lower for kw in ["input=usdc", "input=sol", "in=usdc", "in=sol"]):
                return "buy"
            elif any(kw in msg_lower for kw in ["output=usdc", "output=sol", "out=usdc", "out=sol"]):
                return "sell"
    return None


def direction_log(wallet,client,address,name):
    block_time, example_tx,latest_signature = get_meta(client, address)
    date = datetime.fromtimestamp(block_time).strftime('%Y-%m-%d %H:%M:%S')
    if example_tx:
        # 分析交易方向
        direction = analyze_transaction_direction(
            address,
            example_tx,
            quote_token_mint="SOL")

        signature_txt = wallet.get("last_signature", "")
        if signature_txt == latest_signature:
            return None
        else:
            wallet['last_signature'] = latest_signature
            print(f"{date} {name} {direction}")
    else:
        print("无有效交易")


if __name__ == "__main__":

    wallet_list = [
        {"name": "frank", "address": "CRVidEDtEUTYZisCxBZkpELzhQc9eauMLR3FWg74tReL", "last_signature": ""},
        {"name": "dnf", "address": "DNfuF1L62WWyW3pNakVkyGGFzVVhj4Yr52jSmdTyeBHm", "last_signature": ""},
    ]

    rpc_client = rpc_client()
    while True:
        threads = []
        for wallet in wallet_list:
            thread = threading.Thread(target=direction_log,args=(wallet,rpc_client,wallet['address'],wallet['name']))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        time.sleep(3)