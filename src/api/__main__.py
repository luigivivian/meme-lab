"""Ponto de entrada: python -m src.api [--port 8000] [--ngrok TOKEN]"""

import argparse

from src.api.app import start_server

parser = argparse.ArgumentParser(description="Clip-Flow API Server")
parser.add_argument("--port", type=int, default=8000, help="Porta do servidor")
parser.add_argument("--ngrok", type=str, default=None, help="Token ngrok para expor publicamente")

args = parser.parse_args()
start_server(port=args.port, ngrok_token=args.ngrok)
