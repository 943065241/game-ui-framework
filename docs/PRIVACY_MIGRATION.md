# GUIF Theme Privacy Migration

This guide separates private user Theme data from framework and project Git repositories. It also explains the limits of current-tree cleanup.

## 1. Stop new exposure

Before migration:

- stop committing Theme files, conversation exports, Task Runs, Prompt IR, or review records;
- do not copy private Theme content into README examples, tests, issues, pull-request descriptions, commit messages, or release notes;
- avoid creating a public issue that repeats exposed private content;
- preserve a secure backup before deleting or rewriting anything.

## 2. Configure private storage

Set a private parent directory when the default hidden sibling location is not appropriate:

```bash
export GUIF_DATA_HOME=/secure/private/guif
```

On Windows PowerShell:

```powershell
$env:GUIF_DATA_HOME = "D:\Private\GUIF"
```

The effective store is namespaced by a deterministic workspace key.

## 3. Migrate legacy project Theme files

Python:

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
report = runtime.migrate_legacy_project_themes(
    "SampleGame",
    actor="migration-owner",
)
```

The migration:

1. imports `projects/<project>/themes/*.json` into `PrivateThemeStore`;
2. preserves a private migration archive and report;
3. removes project-local Theme files;
4. removes `current_theme` and `theme_binding` from `project.json`;
5. recreates the active selection as a private Project binding.

Review the migration report before deleting backups.

## 4. Migrate Task Runs and Plans

New GUIF Runs and natural-language Plans are written to private storage automatically.

Legacy directories may still exist:

```text
projects/<project>/runs/
projects/<project>/plans/
```

Treat them as potentially private. Back them up to a secure location, verify that required Task evidence can be read or imported, and then remove them from the working tree. Do not commit the backup.

## 5. Audit the current working tree

```python
report = runtime.audit_privacy(
    sensitive_terms=(
        "a private project phrase",
        "a private Theme name",
    ),
)
```

The audit checks common private-data paths, project-local bindings, and caller-supplied sensitive terms. Reports are written to private storage.

A passing current-tree audit means only that the checked working tree did not contain the configured indicators. It is not proof that historical or external copies have been removed.

## 6. Review non-file exposure surfaces

Inspect:

- README and documentation;
- tests and fixtures;
- commit subjects and bodies;
- branch names and tags;
- issue and pull-request titles, bodies, comments, reviews, and diffs;
- GitHub Actions logs and uploaded artifacts;
- releases and source archives;
- package registries;
- screenshots and attached images;
- forks, mirrors, and external clones.

Replace public examples with wholly fictional data unrelated to any user project.

## 7. Decide whether Git history must be rewritten

A history rewrite is destructive and is not performed automatically by GUIF.

Rewrite may be appropriate when private content exists in reachable commits or tags and the repository owner accepts the operational impact. Before proceeding:

1. identify exact file paths, strings, commits, branches, tags, and releases;
2. make a secure bare backup;
3. freeze merges and coordinate with collaborators;
4. close or rebase open pull requests that depend on old history;
5. choose a tested rewrite rule, commonly using `git filter-repo`;
6. validate the rewritten repository locally;
7. force-push affected branches and tags;
8. replace releases and package artifacts;
9. ask collaborators to delete old clones and re-clone;
10. request hosting-provider cache cleanup where available.

Example patterns must be adapted to the confirmed incident scope. Do not run a broad rewrite merely because a keyword resembles private content.

## 8. Limits of history cleanup

Even after a successful rewrite, the repository owner cannot guarantee deletion from:

- forks outside their control;
- archived source packages;
- search-engine or platform caches;
- screenshots;
- copied patches;
- downloaded workflow logs;
- external clones and backups.

Document the response and avoid claiming complete revocation.

## 9. Prevent recurrence

Keep the following controls enabled:

- `.gitignore` rules for private GUIF data;
- repository privacy tests;
- private Theme ID/version/hash references rather than full content;
- fictional test fixtures;
- review of docs, PR bodies, and CI logs before publication;
- explicit user approval before exporting any private snapshot into a project repository.

## 10. Safe project snapshots

A project may eventually need a Theme snapshot for reproducible builds. Such export must be an explicit operation with:

- user approval;
- destination classification;
- redaction options;
- an immutable snapshot hash;
- clear indication that the content will enter project Git;
- rollback and deletion guidance.

GUIF alpha.23 does not export full private Theme content into project Git by default.
