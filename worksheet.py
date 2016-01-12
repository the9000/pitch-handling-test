# exploring the data

with open('pitch_example_data') as f:
    data = f.readlines()

assert set(x[0] for x in data) == {'S'} 

# The initial 'S' is not covered in the spec. Cut it away.

peeled_data = [x[1:-1] for x in data]  # cut 'S' and '\n'.

# If it is removed, the rest works as per spec.

# All timestamps at 0:8 are numeric:
assert all(x[0:8].isdigit() for x in peeled_data)

# Message types are limited to a known set
message_set = set(x[8] for x in peeled_data)
print(message_set)  # A E P X -> we can ignore other messages for now :)

is_base36 = lambda s: all('0' <= x <='9' or 'A' <= x <= 'Z' for x in s)

# order IDs are all base36
assert all(is_base36(x[9:12]) for x in peeled_data)

