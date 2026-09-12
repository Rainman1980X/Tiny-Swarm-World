# RC1-R03 Remaining Risks

- No qualified protected WSL2 runner/target was available for this branch.
- Host restart and managed partial-failure recovery remain unobserved.
- The full runner now includes the required phases, but its success state can
  only be established by a real candidate run.
- Native-Linux parity is owned by RC1-R02, which is already closed as a
  historical baseline and must be checked for applicability to the integrated
  candidate.
