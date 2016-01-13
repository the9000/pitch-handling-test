## This is code for a test task. Nothing to see here, please walk by.

Provided that you have test pitch data, run:

    cat pitch_example_data | python summer.py

You will get a nice table, as requested. On my laptop it takes ~350 ms.

As a bonus, you can change the number of top results:

    cat pitch_example_data | python summer.py 3

This will only show top 3.

To run tests:

    python pitch_handling_test.py

## Notes

* The code does not work under Python 3 due to the way `OrderStateRecord.updated` is written;
  it would be easy to fix.
* Parsing errors currently just crash the whole thing. Nicer messages are easy to achieve.
  Making parsing errors non-fatal is realtively easy to achieve, too, but the validity of the results
  would need consideration then.
* A few logical errors are detected and reported, if any, but the example data contain no such errors.
