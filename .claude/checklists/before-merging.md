# Before Merging Checklist

Run before merging a feature branch to master.

## 1. All Tasks Done

- [ ] All tasks in the sprint are PASS in UAT
- [ ] No FAIL test cases remaining (PARTIAL is documented with justification)

## 2. Code Review

- [ ] `/simplify` run on all changed files
- [ ] No security vulnerabilities (no eval, no raw SQL with user input)
- [ ] No `print()` statements left in Python code
- [ ] No `console.log()` left in production Vue code

## 3. Migration Safe

- [ ] `bench --site miyano migrate` runs clean
- [ ] No breaking changes to existing DocType fields (additive only)
- [ ] If field removed: migration script provided

## 4. Fixtures Updated

- [ ] Any new Workflow, Role, or Custom Field exported to fixtures
- [ ] `assetcore/hooks.py` fixtures list updated if needed

## 5. Branch State

```bash
git diff master --stat        # confirm scope
git log master..HEAD --oneline # confirm commits
```

- [ ] Only feature-related commits on this branch
- [ ] Commit messages are descriptive (feat/fix/refactor + module reference)

## 6. UAT Sign-off

- [ ] Run: `bench --site miyano execute assetcore.uat_test.run_all`
- [ ] Result: PASS rate ≥ 30/32 (Wave 1 baseline)
- [ ] Any new UAT cases added for this feature
