# RC1 Candidate Evidence Matrix

This matrix records candidate-specific CI evidence. A result is valid only
when its analyzed or executed SHA is recorded; a prior green result does not
qualify a later candidate.

| Candidate | Check | Result | Evidence |
|---|---|---|---|
| db8a50e43e651ca2ac8aa45f44be61439cc50e75 | Python Quality Gate | PASS | [run 34686345018](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34686345018) |
| db8a50e43e651ca2ac8aa45f44be61439cc50e75 | Python Compatibility | PASS | [run 34686345023](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34686345023) |
| db8a50e43e651ca2ac8aa45f44be61439cc50e75 | SonarCloud main analysis | FAIL | [run 34686480442](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34686480442); analysis 4ad4057a-1636-41a2-babd-d78c47b55d30 |
| b870e0abb4b09aaa6b0c684d91bcb47d56c44662 | RC1-R01 implementation PR | PENDING | [PR #321](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/pull/321) |

The failed Sonar analysis reported new reliability rating 3 against
threshold 1 and new security rating 5 against threshold 1. New
maintainability, coverage, duplication and reviewed-hotspot conditions were
within threshold. The replacement result for the integrated final candidate
is still pending.
