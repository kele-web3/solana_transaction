from solana.rpc.api import Client
from solana.rpc.commitment import Finalized
from solders.solders import Pubkey


def get_signature(smart_wallet):
    client = Client("https://api.mainnet-beta.solana.com")
    if client.is_connected():
        signatures = client.get_signatures_for_address(account=Pubkey.from_string(smart_wallet),
                                                       limit=10,
                                                       commitment=Finalized).value
        print(signatures)
    else:
        print("主网连接失败")


if __name__ == '__main__':
    smart_wallet = "Ay9wnuZCRTceZJuRpGZnuwYZuWdsviM4cMiCwFoSQiPH"
    get_signature(smart_wallet)
