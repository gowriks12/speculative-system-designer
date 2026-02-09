import json
from pathlib import Path
from server.tools.simulate_future import simulate_future
ROOT_PATH = Path(__file__).parent.parent.parent
print(ROOT_PATH)
# FUTURES_PATH = ROOT_PATH + Path("data\futures.json")
FUTURES_PATH = "C:\\Users\\gowri\\Documents\\Projects\\MCP\\SpeculativeSystemDesigner\\data\\futures.json"

def evaluate_architecture(description: str) -> dict:
    with open(ROOT_PATH / "data/futures.json", "r") as f:
        futures = json.load(f)
    # futures = json.loads(FUTURES_PATH)

    critiques = []

    for future_id in futures.keys():
        critique = simulate_future(future_id, description)
        critiques.append(critique)

    print(critiques)
    return {
        "status": "evaluation_complete",
        "critique_count": len(critiques),
        "critiques": critiques
    }

# result = evaluate_architecture("Design a scalable backend system where events are ingested asynchronously via a message queue (e.g., Kafka) to decouple producers from consumers and ensure high throughput. Event data is then processed in real-time or batch using a stream processing framework (e.g., Apache Flink or Spark Streaming) to transform, aggregate, and enrich the events. Processed data is stored in a fast, query-optimized database (e.g., a time-series or columnar store like ClickHouse or Druid). Finally, a RESTful or GraphQL analytics API layer exposes aggregated insights and customizable metrics to customers, supported by caching (e.g., Redis) to ensure low-latency response times. The system can horizontally scale at each layer to handle growing event volumes and query loads.")
# print(result)