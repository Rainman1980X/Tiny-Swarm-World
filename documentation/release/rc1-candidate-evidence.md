# RC1 Candidate Evidence Matrix

This matrix records candidate-specific CI evidence. A result is valid only
when its analyzed or executed SHA is recorded; a prior green result does not
qualify a later candidate. The following first table is historical.

| Candidate | Check | Result | Evidence |
|---|---|---|---|
| db8a50e43e651ca2ac8aa45f44be61439cc50e75 | Python Quality Gate | PASS | [run 34686345018](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34686345018) |
| db8a50e43e651ca2ac8aa45f44be61439cc50e75 | Python Compatibility | PASS | [run 34686345023](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34686345023) |
| db8a50e43e651ca2ac8aa45f44be61439cc50e75 | SonarCloud main analysis | FAIL | [run 34686480442](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34686480442); analysis 4ad4057a-1636-41a2-babd-d78c47b55d30 |
| b870e0abb4b09aaa6b0c684d91bcb47d56c44662 | RC1-R01 implementation PR | PENDING | [PR #321](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/pull/321) |

The failed Sonar analysis reported new reliability rating 3 against
threshold 1 and new security rating 5 against threshold 1. New
maintainability, coverage, duplication and reviewed-hotspot conditions were
within threshold. That failure is retained and superseded by the observed
candidate results below.

## Integrated product candidate, 2026-09-13

Main candidate: `c921e69533450fba86d908e2990c106bef87769a` (PR #335).
Its complete Git tree `a14e635dd22cb02fc063a319d73383f676572bca` equals PR head
`8eb5db338aed9965a49ed6879198fd1053b97dcc`. Executed SHAs remain distinct.

| Executed candidate | Check | Result | Evidence |
|---|---|---|---|
| 8eb5db338aed9965a49ed6879198fd1053b97dcc | PR Python Quality | PASS | [34725658814](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725658814) |
| 8eb5db338aed9965a49ed6879198fd1053b97dcc | PR Python 3.12/3.13 | PASS | [34725658760](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725658760) |
| 8eb5db338aed9965a49ed6879198fd1053b97dcc | PR SonarCloud waited gate | EXTERNAL_GATE_VERIFIED | [34725802800](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725802800) |
| c921e69533450fba86d908e2990c106bef87769a | Main Python Quality | PASS | [34726339297](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34726339297) |
| c921e69533450fba86d908e2990c106bef87769a | Main Python 3.12/3.13 | PASS | [34726339319](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34726339319) |
| c921e69533450fba86d908e2990c106bef87769a | Main SonarCloud waited gate | EXTERNAL_GATE_VERIFIED | [34726472444](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34726472444) |
| 8eb5db338aed9965a49ed6879198fd1053b97dcc | Fresh dependency/SBOM/Trivy config scan | PASS, exact whole-tree equivalence to main verified | [Provenance](../../.tiny-swarm/evidence/issue-300/candidate-c921e695/provenance.json) |

The PR Sonar workflow metadata uses 2183006e, but actual checkout and SCM revision
are 8eb5db33. The separate main scanner analyzed c921e695. Both waited for the
quality-gate result. The R04 CA-copy repair is merged in PR #330; no rules or
meaningful scanner scope were weakened. The preceding failed analysis
b683560c-2f9a-4179-a6f3-aca64e2f6ec2 on 9db13571 remains historical evidence.

The scan covers 13 locked Python dependencies and three Dockerfiles (60 successful
checks, no HIGH/CRITICAL configuration findings). Built-image vulnerability status
and live acceptance are separate. RC1-E09 owns the final all-row decision and
records required hosted checks for the final evidence integration revision.
