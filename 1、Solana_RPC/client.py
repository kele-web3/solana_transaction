from solana.rpc.api import Client


def rpc_client():
    client = Client("https://api.mainnet-beta.solana.com")
    if client.is_connected():
        print("主网连接成功")
        res = client.get_block_height()
        print(res)
        return res
    else:
        print("主网连接失败")


if __name__ == '__main__':
    rpc_client()
