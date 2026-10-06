from logger import logger
import argparse
from Server import async_tcp
from Config import config

def setupFlags():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="host for the dice server"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=7379,
        help="port for the dice server"
    )

    args = parser.parse_args()
    config.host = args.host
    config.port = args.port

def main ():
    setupFlags()
    print("Rolling the Dice Server")
    # sync_tcp.RunSyncTCPServer()
    async_tcp.RunAsyncTCPServer()



if __name__ == "__main__":
    main()