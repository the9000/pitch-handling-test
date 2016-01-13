"""Track sales in a PITCH stream, find N most sold stock symbols."""

from collections import defaultdict
import sys

from pitch_handling import handleMessage


def processLine(orders, failures, summary, line):
    outcome = handleMessage(orders, line)
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


def processLines(lines):
    # This is basically a reduce / fold with (orders, failures, summary) as the value.
    orders = {}  # order number -> OrderStateRecord
    failures = []
    summary = defaultdict(int)  # ticker -> current sum

    for line in lines:
        # We assume nothing about passed variables being mutateb by the call.
        orders, failures, summary = processLine(orders, failures, summary, line)

    # remaining orders might be used to further processing; failures can be reported.
    return orders, failures, summary


def findTopN(lines, n=10):
    _, failures, summary = processLines(lines)
    by_ticker = [(amount, ticker) for (ticker, amount) in summary.iteritems()]
    by_ticker.sort()  # sorts by amount, then by ticker

    # print the results nicely. negatives because the sorting was ascending.
    for amount, ticker in  by_ticker[:-(n+1):-1]:
        print '{:6s} {:14d}'.format(ticker, amount)

    # Just in case.
    if failures:
        print '* {:d} failures registered during processimg.'.format(len(failures))


def main():
    lines = (x[1:] for x in sys.stdin)  # lazily cut the initial 'S'
    if len(sys.argv) == 2:
        n = int(sys.argv[1])  # we support passing the n on command line
    else:
        n = 10
    findTopN(lines, n)


if __name__ == '__main__':
    main()
