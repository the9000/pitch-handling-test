# exploring the data

with open('pitch_example_data') as f:
    data = f.readlines()

print('Read %d rows' % len(data))

def sanityCheck(data):
    assert set(x[0] for x in data) == {'S'} 

    # The initial 'S' is not covered in the spec. Cut it away.
    peeled_data = [x[1:-1] for x in data]  # cut 'S' and '\n'.


    # All timestamps at 0:8 are numeric:
    timestamps = [x[0:8] for x in peeled_data]
    assert all(x.isdigit() for x in timestamps)

    # Are timestamps monotonous?
    timestamp_jumps = [(pred, succ) for pred, succ in zip(timestamps, timestamps[1:]) if pred > succ]
    print('Timestamp jumps: %d'% len(timestamp_jumps))  # no, 691 jump

    # We still assume that timestamps for thesamemessage ID are monotonous.


    # Message types are limited to a known set
    message_set = set(x[8] for x in peeled_data)
    print(message_set)  # A E P X -> we can ignore other messages for now :)

    is_base36 = lambda s: all('0' <= x <='9' or 'A' <= x <= 'Z' for x in s)

    # order IDs are all base36
    assert all(is_base36(x[9:12]) for x in peeled_data)

# rough summing
# A: add; create a new order / resurrects canceled order.
# E: execute; order is removed, sale amount calculable.
# P: trade; execution of a hidden order.
# X: cancel; (a part of) order is removed.

# Note: technically we could ignore A and X messages and only sum P and E messages.
# We'll track A and X and do some stream validation, though.

from collections import defaultdict
from collections import namedtuple


class Record(namedtuple('Record', ['order_id', 'timestamp', 'ticker', 'amount', 'price'])):
    def withNewAmount(self, amount):
        prev_values_map = self._asdict()
        prev_values_map.update(amount=amount)
        return Record(**prev_values_map)


class Success(namedtuple('Success', ['record', 'ticker', 'value'])):
    """Good outcome.
    .record = updated order info to store,
    .ticker = stock symbol of the order,
    .value = transaction sale value.
    """
    # We could have overridden __bool__ instead,
    # but it would break the convention that falsy values carry no data.
    @property
    def success(self):
        return True

        
class Failure(namedtuple('Failure', ['order_id', 'timestamp', 'message'])):
    """Bad outcome. .message = human-readable error message."""
    @property
    def success(self):
        return False
    def __str__(self):
        # debugging aid
        return '%s: order %s at %s' % (self.message, to36(self.order_id), self.timestamp)

        
def to36(n):
    result = []
    while n != 0:
        n, rem = divmod(n, 36)
        if rem <= 9:
            digit = str(rem)
        else:
            digit = chr(65 + rem - 10)
        result.append(digit)
    if not result:
        return '0'
    else:
        result.reverse()
        return ''.join(result)

    

def handleAdd(prev_record, timestamp, order_id, line):
    if prev_record:
        # Do not try to update the order, what if the price is different?
        return Failure(order_id, timestamp, 'Duplicate Add record')
    amount = int(line[22:28])
    ticker = line[28:34]
    price = int(line[34:44])
    new_record = Record(order_id, timestamp, ticker, amount, price)
    return Success(new_record, ticker, 0)
    

def handleCancel(prev_record, timestamp, order_id, line):
    if not prev_record:
        return Failure(order_id, timestamp, 'Cannot cancel order, it was never added')
    amount = int(line[21:27])
    if amount > prev_record.amount:
        return Failure(order_id, timestamp, 'Trying to cancel %d shares when only got %d' % (
            amount, prev_record.amount
        ))
    new_record = prev_record.withNewAmount(prev_record.amount - amount)
    return Success(new_record, prev_record.ticker, 0)


def handleExecute(prev_record, timestamp, order_id, line):
    # NOTE: the logic is damn similar to canceling.
    if not prev_record:
        return Failure(order_id, timestamp, 'Cannot execute order, it was never added')
    amount = int(line[21:27])
    if amount > prev_record.amount:
        return Failure(order_id, timestamp, 'Trying to execute %d shares when only got %d' % (
            amount, prev_record.amount
        ))
    sale_value = amount * prev_record.price
    new_record = prev_record.withNewAmount(prev_record.amount - amount)
    return Success(new_record, prev_record.ticker, sale_value)

        
def handleTrade(prev_record, timestamp, order_id, line):
    # We can assume that prev_record is empty.
    # We just trust the trade info and don't track any changes.'
    amount = int(line[22:28])
    ticker = line[28:34]
    price = int(line[34:44])
    return Success(None, ticker, price * amount)
    
        
handlers = {
    'A': handleAdd,
    'E': handleExecute,
    'P': handleTrade,
    'X': handleCancel,
}


def processLine(orders, line):
    timestamp = int(line[0:8])
    msg_type = line[8]
    order_id = int(order_36, 36)
    prev_record = orders.get(order_id)
    if prev_record and prev_record.timestamp > timestamp:
        return Failure(order_id, timestamp, 'Event %r from past; already seen %d' % (
            msg_type, prev_record.timestamp))
    
    handler = handlers.get(msg_type)
    if not handler:
        return Failure('Unknown message type %r at timestamp %d' % (msg_type, timestamp))
    return handler(prev_record, timestamp, order_id, line)


def doOneLine(orders, failures, summary, line):
    outcome = processLine(orders, line)
    if outcome.success:
        summary[outcome.ticker] += outcome.value
        if outcome.record:  # trades return no records
            order_id = outcome.record.order_id
            if outcome.record.amount:
                orders[order_id] = outcome.record
            else:
                del orders[order_id]  # the order was completly executed / closed.
    else:
        failures.append(outcome)
    return orders, failures, summary
            
    
def doLines(lines):
    orders = {}  # order number -> Record
    failures = []
    summary = defaultdict(int)  # ticker -> current sum

    for line in lines:
        orders, failures, summary = doOneLine(orders, failures, summary, line)

    return orders, failures, summary


def findTopN(lines, n=10):
    _, _, summary = doLines(lines)
    by_ticker = [(amount, ticker) for (ticker, amount) in summary.iteritems()]
    by_ticker.sort()  # sorts by amont, then by ticker
    return by_ticker[:n]