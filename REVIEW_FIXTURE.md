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
