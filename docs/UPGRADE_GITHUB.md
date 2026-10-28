# Update GitHub repository using the v1.1 ZIP

The assistant's GitHub connection is **read-only**, so this package is not automatically published. Back up your current repo before replacing files.

Option A (source ZIP):
1. `git clone https://github.com/phamtung17/dsh-autocad-TCVN.git`
2. Download and extract the release ZIP and copy its `CAD_DSH_Agent/` *contents* into the cloned root. Keep your own project-specific DWT files and local rules separately.
3. Confirm `.github/workflows/ci.yml` exists, and remove any obsolete duplicate workflow if present.
4. `python -m pip install -r requirements-test.txt`
5. `python -m pytest tests -q` and `python tools/check_skills.py`
6. `git status`, review all changes, `git add .`, `git commit -m "Release AutoCAD DSH Agent v1.1.0"`, and `git push origin main` using your own GitHub permission.

Option B (`.patch`, for a closely matching v1.0 tree):
- With clean current branch in repository root, `git apply --check ../DSH_AutoCAD_v1.0_to_v1.1.patch`, then `git apply ../DSH_AutoCAD_v1.0_to_v1.1.patch`.
- If upstream files diverged, use the ZIP replacement selectively and review diffs; never force-apply a patch without inspection.

After pushing, verify the **actual** GitHub Actions matrix result; check downloaded report JSON includes your commit SHA and success status. GitHub's CI does not contain AutoCAD and cannot confirm COM behavior.
