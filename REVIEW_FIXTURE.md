# Code review agent test fixture — do not merge

This draft branch intentionally contains defects for evaluating `code-review-agent`.
The new helpers are not imported by the Streamlit app and do not place trades.
The defects are deliberately retained; this is not a production-ready feature.

## Expected findings (evaluation ground truth)

1. **Security:** `load_target_weights` calls `pickle.loads` on uploaded bytes.
   A malicious pickle can execute code before conversion/validation. Use a data-only
   format such as JSON with schema validation. Do not exercise malicious payloads.
2. **Correctness:** `build_rebalance_preview` applies `abs` to value changes,
   converting required sales into additions. A 600/400 portfolio targeting 40/60
   should produce -200/+200, rather than +200/+200. Omitted existing positions
   should similarly receive a negative liquidation value.
3. **Validation:** the complete allocation is never checked for finite, nonnegative
   weights totaling 100%. Targets totaling 120%, negative targets, or NaN values
   should be rejected instead of producing an invalid plan.
4. **Test coverage:** happy-path tests pass while omitting the sell direction,
   liquidation, invalid-total, negative-weight, NaN, malformed-file and zero-value
   portfolio cases. Suggested tests should include concrete inputs/assertions.

For a clean control, remove the pickle importer, preserve signed changes, validate
inputs, and add the missing regression cases on a separate branch. Do not merge
this deliberately defective branch into the application.

## Additional code-quality targets

5. **Duplicate-position overwrite:** `aggregate_position_values` assigns rather
   than accumulates each normalized symbol. Positions AAPL=250 and AAPL=750
   from different accounts should aggregate to AAPL=1000, but return AAPL=750.
   Normalization collisions such as `" aapl "` and `"AAPL"` have the same issue.
6. **Wrong ranking direction:** `top_holdings` sorts values ascending despite
   promising largest-first order. For AAPL=800, MSFT=150, GOOG=50 with limit=2,
   the expected symbols are `["AAPL", "MSFT"]`; actual results are
   `["GOOG", "MSFT"]`.
7. **Limit validation:** `top_holdings` documents a positive limit but accepts
   zero/negative limits. A negative limit silently applies Python negative slicing
   rather than rejecting the invalid input.

## Additional test-coverage targets

- `test_aggregate_position_values_with_unique_symbols` never supplies duplicate
  symbols across accounts or normalization collisions. Add repeated-symbol inputs
  and assert the combined value, independently of input ordering.
- `test_top_holdings_with_one_position` cannot distinguish ascending from descending
  sorting. Add unequal multiple holdings and assert their exact ordered symbols.
- `test_top_holdings_limits_result_count` checks only length, so it passes while
  returning the wrong holdings. Assert `result == ["AAPL", "MSFT"]` for its inputs.
- No tests cover empty rankings, limits larger than the holdings count, zero or
  negative limits, or an empty aggregate. Zero/negative limits should raise
  `ValueError`; empty valid inputs should return an empty result.

All six supplied tests deliberately pass on this branch. They are incomplete test
examples, not a claim that the helpers are correct. These additions stay outside
the live Streamlit application and remain part of the **do not merge** fixture.
