from server.tools.submit_architecture import submit_architecture
from server.tools.simulate_future import simulate_scaling_future
from server.tools.declare_tradeoff import declare_tradeoff

architecture_text = """
The system uses a single processing service with synchronous
event handling and some operational steps.
"""

print("\n--- Submitting Architecture ---")
submission = submit_architecture(architecture_text)
print(submission)

if submission["status"] != "accepted":
    exit()

print("\n--- Simulating Scaling Future ---")
future = simulate_scaling_future(architecture_text)
print(future)

critique_id = future["critique"]["id"]

print("\n--- Declaring Tradeoff ---")
tradeoff = declare_tradeoff(
    critique_id,
    "We accept limited horizontal scalability in exchange for simpler operational control in the first year."
)
print(tradeoff)
