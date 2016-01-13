"""Handling of PITCH messages.

A result of a handler invocation is either a Success or a Failure.
No exceptions are deliberately thrown.
"""

from collections import defaultdict
from collections import namedtuple


class OrderStateRecord(namedtuple('Record', ['order_id', 'timestamp', 'ticker', 'amount', 'price'])):
    """Order state record, represents an open order.
    .order_id = order ID.
    .timestamp = timestamp of last message related to this order.
    .ticker = stock symbol; set by an Add message..
    .amount = number of shares; set by an Add message.
    .price = per-share price; set by an Add message."""
    def updated(self, timestamp, amount):
        """Returns a new instance with amount ant timestamp updated."""
        prev_values_map = self._asdict()
        prev_values_map.update(timestamp=timestamp, amount=amount)
        return OrderStateRecord(**prev_values_map)


class Success(namedtuple('Success', ['record', 'ticker', 'value'])):
    """Good outcome.
    .record = updated order info to store, if any.
    .ticker = stock symbol of the order.
    .value = transaction sale value.
    """
    # We could have overridden __bool__ instead,
    # but it would break the convention that falsy values carry no data.
    @property
    def success(self):
        return True

        
class Failure(namedtuple('Failure', ['order_id', 'timestamp', 'message'])):
    """Bad outcome.
    .order_id = id of the order for which a failure occurred.
    .timestamp = timestamp of the message that a handler failed to process.
    .message = human-readable error message.
    """
    # We should store the entire orginal message to simplify troubleshooting.
    @property
    def success(self):
        return False
    def __str__(self):
        # debugging aid
        return '%s: order %s at %s' % (self.message, to36(self.order_id), self.timestamp)


# This function likely would already exist in some utility package.
def to36(n):
    """Returns a base-36 representation of n."""
    result = []
    while n != 0:
        n, rem = divmod(n, 36)
        if rem <= 9:
            digit = str(rem)
        else:
            digit = chr(rem - 10 + 65) # ord('A') = 65, unless we're running on EBCDIC. 
        result.append(digit)
    if not result:
        return '0'
    else:
        result.reverse()
        return ''.join(result)


# Note: currently handlers assume well-formed messages and would just crash or misbehave
# on an ill-formed message. A production-quality code would include more robust paersing
# that would not crash the entire pipeline due to an incorrect message,

    
def handleAdd(prev_record, timestamp, order_id, line):
    if prev_record:
        # Do not try to update the order, what if the price is different?
        return Failure(order_id, timestamp, 'Duplicate Add record')
    amount = int(line[22:28])
    ticker = line[28:34]
    price = int(line[34:44])
    new_record = OrderStateRecord(order_id, timestamp, ticker, amount, price)
    return Success(new_record, ticker, 0)
    

def _handleOrderDecrease(prev_record, timestamp, order_id, line, is_sale):
    # both handleCancel and handleExecute essentially do the same; factored it out.
    if not prev_record:
        return Failure(order_id, timestamp, 'Cannot execute order, it was never added')
    amount = int(line[21:27])
    if amount > prev_record.amount:
        return Failure(order_id, timestamp, 'Trying to execute %d shares when only got %d' % (
            amount, prev_record.amount
        ))
    new_record = prev_record.updated(timestamp, prev_record.amount - amount)
    # If we had more variants of sale value calculation, we'd pass a function to calculate it.
    sale_value = amount * prev_record.price if is_sale else 0
    return Success(new_record, prev_record.ticker, sale_value)


def handleCancel(prev_record, timestamp, order_id, line):
    # Canceling always result in zero sales.
    return _handleOrderDecrease(prev_record, timestamp, order_id, line, is_sale=False)


def handleExecute(prev_record, timestamp, order_id, line):
    return _handleOrderDecrease(prev_record, timestamp, order_id, line, is_sale=True)


def handleTrade(prev_record, timestamp, order_id, line):
    # We can assume that prev_record is empty.
    # We just trust the trade info and don't track any changes.
    amount = int(line[22:28])
    ticker = line[28:34]
    price = int(line[34:44])
    return Success(None, ticker, price * amount)
    
        
handler_by_message_type = {
    'A': handleAdd,
    'E': handleExecute,
    'P': handleTrade,
    'X': handleCancel,
}


def handleMessage(orders, message):
    """Parse and react upon one message.
    Args:
      orders: a dict {order_id: OrderStateRecord}; not updted by the call.
      messge: a well-formed message (normally an entire line).

    Returns:
      a Success (usually contains a new order status) or a Failure (with an explanation).
    """
    timestamp = int(message[0:8])
    msg_type = message[8]
    order_id = int(order_36, 36)
    prev_record = orders.get(order_id)
    if prev_record and prev_record.timestamp > timestamp:
        return Failure(order_id, timestamp, 'Event %r from past; already seen %d' % (
            msg_type, prev_record.timestamp))
    
    handler = handler_by_message_type.get(msg_type)
    if not handler:
        return Failure(oredr_id, timestamp, 'Unknown message type %r' % msg_type)
    return handler(prev_record, timestamp, order_id, message)
