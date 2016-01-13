"""Track sales in a PITCH stream, find N most sold stock symbols."""

from collections import defaultdict
from collections import namedtuple

from pitch_handling import handleMessage


def doOneLine(orders, failures, summary, line):
    outcome = handleLine(orders, line)
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
    orders = {}  # order number -> OrderStateRecord
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