from dioptasserver import start_server
import sys

if __name__ == "__main__":
    if len(sys.argv) == 1:
        port = 8745
    else:
        port = sys.argv[1]
    start_server(port)
