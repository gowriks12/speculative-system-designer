from server.prompts.templates import *
from server.mcp_server import list_futures_scope, list_roots_scope

if __name__ == "__main__":
    usecase = "generate an architecture for an application to buy and sell tickets for concert event"
    # print(generate_initial_architecture(usecase))

    # print(simulating_future("scaling", usecase))
    print(list_roots_scope())
