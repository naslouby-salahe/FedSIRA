You are responsible for **RESUMING and completing the ENTIRE FedSIRA repository from its current state through the final milestone**.

This is a **continuation of existing work**.

A significant portion of **Milestone 1 may already be implemented locally**. Do **NOT** assume the repository is starting from zero, and do **NOT** blindly redo Milestone 1.

Your first responsibility is to reconstruct the exact current state from:

* the local working tree;
* local commits;
* the current branch;
* remote state;
* live GitHub issues;
* live GitHub milestones;
* issue checklists and acceptance criteria;
* existing tests;
* existing implementation.

Then **resume from the first genuinely incomplete requirement**.

The objective is still the complete repository:

```text
Reconstruct current progress
→ Preserve correct existing work
→ Identify completed / partial / missing Milestone 1 work
→ Resume the first incomplete issue or acceptance criterion
→ Finish Milestone 1
→ Continue milestone by milestone
→ Issue by issue
→ Implement
→ Test
→ Audit
→ Commit
→ Push
→ Verify acceptance criteria
→ Fix anything missing
→ Update verified issue checklist
→ Close issue
→ Complete milestone audit
→ Fix milestone deficiencies
→ Close milestone
→ Run SonarQube API audit
→ Fix SonarQube findings
→ Continue to next milestone
→ Final ticket-by-ticket hostile audit
→ Final architecture hostile audit
→ Final real-data contract audit
→ Final quality cycle
→ Final SonarQube audit
→ Finish the entire project
```

**Do not restart Milestone 1 merely because this is a new agent cycle.**

**Do not stop after Milestone 1.**

**Do not stop after any subset of milestones or issues.**

The objective of this agent cycle is to finish **ALL implementation milestones and ALL intended GitHub issues in FedSIRA**.

Do not merely report problems you are capable of fixing.

Do not ask me to perform routine implementation, GitHub, validation, audit, research, configuration, scientific, or quality work for you.

Continue until the repository is legitimately complete.

# ABSOLUTE AUTONOMY RULE — I WILL NOT BE AVAILABLE

**I will not be here to answer questions during this agent cycle.**

Therefore:

* DO NOT ask me for clarification.
* DO NOT ask me for confirmation.
* DO NOT ask me which implementation I prefer.
* DO NOT ask me to choose between alternatives.
* DO NOT ask me for missing scientific constants.
* DO NOT ask me what a roadmap sentence means.
* DO NOT ask me which dataset field to use.
* DO NOT ask me which library behavior is intended.
* DO NOT ask me whether you should fix something.
* DO NOT ask me whether you should proceed.
* DO NOT pause waiting for approval.
* DO NOT terminate merely because something is ambiguous.

For every ambiguity, missing value, unclear requirement, undocumented behavior, incomplete acceptance criterion, missing dataset detail, unclear scientific definition, version-sensitive library behavior, or implementation decision, resolve it yourself using the strongest available evidence.

Use this resolution order:

1. repository-local agent instructions;
2. `docs/Roadmap.md`;
3. live GitHub issue bodies, comments, dependencies, acceptance criteria, and milestone context;
4. existing source code, tests, configuration, and Git history;
5. official documentation and specifications;
6. primary research papers;
7. official dataset documentation;
8. official reference implementations/source repositories;
9. other high-quality technical sources;
10. if genuine uncertainty remains, choose the **scientifically strongest, safest, most maintainable, reproducible, conservative, and defensible interpretation**.

When information is missing, **SEARCH ONLINE** rather than inventing it.

This explicitly includes researching:

* numerical constants;
* mathematical definitions;
* statistical procedures;
* algorithm parameters;
* dataset schemas;
* feature definitions;
* labels and class vocabularies;
* target classes;
* dataset sizes;
* client/domain identities;
* temporal semantics;
* split semantics;
* API behavior;
* library behavior;
* serialization;
* software-version semantics;
* scientific formulas;
* standards;
* security properties;
* any other factual clarification required for a defensible implementation.

Prefer:

```text
official specification/documentation
→ primary research paper
→ official dataset documentation
→ official source/reference repository
→ authoritative maintained technical documentation
→ reputable secondary source only when necessary
```

For libraries, verify behavior against the version actually locked by FedSIRA.

For scientific values not explicitly fixed by the roadmap:

* research them;
* prefer primary evidence;
* choose the best-supported interpretation;
* preserve provenance where appropriate;
* centralize the value according to repository rules;
* add tests protecting the chosen contract.

External research may **fill gaps**.

It must **never override an explicit FedSIRA roadmap or repository requirement**.

If external evidence conflicts with the roadmap, the roadmap wins unless the roadmap explicitly states otherwise.

If a genuine external blocker exists, such as an unavailable credential or mandatory third-party service:

* exhaust repository/environment/configuration evidence first;
* never fabricate credentials;
* never expose secrets;
* complete every independent task that remains possible;
* record exact evidence of the blocker;
* continue all work not dependent upon it.

“I need user input” is not an acceptable answer when the ambiguity can reasonably be resolved through research and engineering judgment.

# Repository

Work **ONLY** in:

```text
naslouby-salahe/FedSIRA
```

and its corresponding local repository.

Do not operate on unrelated repositories.

# FIRST — RECONSTRUCT THE CURRENT STATE BEFORE EDITING

This is mandatory because work already exists.

Before making any implementation change:

1. locate the repository root;
2. inspect the current branch;
3. inspect `git status`;
4. inspect staged and unstaged diffs;
5. inspect untracked files;
6. inspect configured remotes;
7. inspect recent commits;
8. inspect ahead/behind state;
9. inspect remote branch state;
10. inspect live GitHub milestones;
11. inspect live GitHub open **and closed** issues;
12. inspect Milestone 1 issue state;
13. inspect which Milestone 1 acceptance criteria appear already implemented;
14. inspect existing tests and architecture tests;
15. identify any pre-existing uncommitted work;
16. determine whether uncommitted work belongs to an active issue, completed issue, or unrelated user work.

Do **not** reset, clean, checkout over, discard, revert, or otherwise destroy legitimate existing work merely to obtain a clean repository.

Do not assume:

* an open issue means no code exists;
* a closed issue means its implementation is correct;
* an unchecked checklist item means nothing exists;
* a checked checklist item proves the implementation;
* an uncommitted diff is disposable;
* a local commit has already been pushed;
* Milestone 1 is incomplete merely because the agent is starting today.

Reconcile all evidence.

# RESUME CONTRACT

For every Milestone 1 issue, classify its current state internally as one of:

```text
VERIFIED_COMPLETE
IMPLEMENTED_BUT_NOT_VERIFIED
PARTIALLY_IMPLEMENTED
NOT_IMPLEMENTED
GITHUB_STATE_DRIFT
```

Use actual evidence.

Examples:

### Code exists and issue is still open

Audit the implementation against the current live issue and roadmap.

If complete:

* run all required checks;
* fix anything found;
* commit only if there are uncommitted corrections;
* push;
* update the verified checklist;
* close the issue.

Do **not** rewrite it from scratch.

### Code is partially implemented

Continue from the existing implementation.

Preserve correct work.

Finish the missing acceptance criteria.

### Code is complete locally but uncommitted

Audit it first.

If legitimate and complete:

* run required checks;
* commit as the appropriate issue-specific commit;
* push;
* verify;
* close only after the post-push audit.

### Commit exists locally but is not pushed

Audit it first.

Push only after confirming it is correct and belongs on the intended branch.

### GitHub says an issue is closed but the final implementation violates its acceptance criteria

Do not preserve an incorrect state merely because the issue was previously closed.

Reopen/fix as appropriate, or otherwise correct the GitHub state according to the available workflow.

### Existing implementation differs from how you would personally design it

If it is correct, maintainable, roadmap-compliant, typed, tested, and architecturally valid:

**KEEP IT.**

Do not generate churn for stylistic preference.

The guiding principle is:

> Resume and complete, not reset and reimplement.

# FIRST — FIND AND OBEY REPOSITORY AGENT INSTRUCTIONS

Before implementation, search the repository root and applicable parent scope for repository-specific agent instructions, including at minimum:

```text
claude.md
CLAUDE.md
AGENTS.md
```

and equivalent explicit agent instruction files.

If any exist:

**READ THEM COMPLETELY FROM BEGINNING TO END BEFORE IMPLEMENTATION.**

Follow their applicable rules exactly.

Repository-defined rules for:

* architecture;
* typing;
* configuration;
* scientific boundaries;
* testing;
* comments/docstrings;
* dependencies;
* naming;
* cleanup;
* backward compatibility;
* workflow;
* hooks;
* datasets;
* outputs;
* results;
* provenance;
* reproducibility;

are mandatory.

If no such instruction file exists, continue.

Do **not** ask me.

# ABSOLUTE SOURCE-OF-TRUTH HIERARCHY

Use this hierarchy throughout:

1. applicable repository-local agent instructions;
2. `docs/Roadmap.md`;
3. live GitHub milestones;
4. live GitHub issues, comments, checklists, dependencies, and acceptance criteria;
5. existing implementation, tests, configuration, and Git history;
6. authoritative external evidence used only for details not defined above.

Read:

```text
docs/Roadmap.md
```

**completely from beginning to end before continuing implementation.**

This is the authoritative FedSIRA scientific, mathematical, architectural, dataset, configuration, experiment, CLI, statistical, artifact, provenance, and reproducibility contract.

Whenever something becomes unclear:

**GO BACK TO `docs/Roadmap.md` FIRST.**

Do not invent conflicting interpretations.

Do not weaken requirements.

Do not substitute stale local planning documents.

Do not rename canonical FedSIRA concepts because another abstraction seems more convenient.

Do not make tests pass by violating the intended scientific contract.

# GITHUB IS THE LIVE WORK QUEUE

Retrieve milestones and issues **DIRECTLY FROM GITHUB**.

Do not use local Markdown copies of:

* issues;
* milestones;
* milestone audits;
* coverage inventories;
* issue exports;
* implementation plans;
* agent notes;
* progress reports;

as substitutes for live GitHub state.

GitHub is authoritative for:

* open/closed state;
* milestone membership;
* issue body;
* issue comments;
* dependencies;
* acceptance criteria;
* checklists;
* labels;
* execution status.

Refresh GitHub continuously throughout the work.

Do not load GitHub once and work from stale state for the rest of the agent cycle.

# ESTABLISH THE COMPLETE REMAINING EXECUTION ORDER

After reconstructing current progress, retrieve **ALL FedSIRA milestones and ALL relevant issues**, not only Milestone 1.

Determine:

* what is already legitimately complete;
* what is partially complete;
* what remains;
* milestone ordering;
* issue ordering;
* explicit dependencies;
* roadmap-implied dependencies;
* shared infrastructure dependencies;
* architecture/testing prerequisites;
* dataset prerequisites;
* scientific prerequisites;
* configuration prerequisites;
* experiment prerequisites;
* quality gates.

Then execute the **remaining work** in dependency-correct order.

Do not redo already verified work just for symmetry.

Do not artificially parallelize dependent work.

Parallel subagents may be used for genuinely independent:

* source inspection;
* issue auditing;
* documentation research;
* dataset-schema research;
* scientific verification;
* architecture auditing;
* test analysis;
* independent implementation.

But an issue is not complete until its **integrated implementation** has been validated.

# NEVER POLLUTE THE REPOSITORY WITH AGENT PLANNING FILES

Do not create:

* `Issues.md`;
* `Milestones.md`;
* issue-plan Markdown;
* milestone-plan Markdown;
* progress Markdown;
* audit scratch Markdown;
* status Markdown;
* agent notes;
* temporary root documents;
* implementation-plan documents.

Do not pollute the root.

If ephemeral scratch files are absolutely unavoidable, use only:

```text
docs/temp/
```

and delete that directory completely before final completion.

Never commit agent scratch material.

# FEDSIRA REAL-DATA CONTRACT

FedSIRA's authoritative roadmap defines the canonical data contract.

At minimum, the roadmap identifies:

```text
Primary dataset:   N-BaIoT
Secondary dataset: CICIoT2023
```

Do not substitute another dataset without an explicit roadmap requirement.

Before implementing or modifying any:

* acquisition;
* adapter;
* schema;
* preprocessing;
* role construction;
* deterministic sampling;
* domain/client partitioning;
* scaling;
* experiment;
* metric;
* evidence computation;

first determine the exact requirement from `docs/Roadmap.md`.

Do **not invent columns**.

Do **not guess labels**.

Do **not guess class order**.

Do **not guess target classes**.

Do **not guess domain identities**.

Do **not guess sample identities**.

Do **not guess split or role semantics**.

Do **not infer scientific contracts from whichever small file is easiest to inspect**.

# SHARED RAW DATA IS IMMUTABLE

Treat:

```text
/home/naslouby/Projects/datp-shared-data/raw
```

as **READ ONLY**.

Never:

* edit raw files;
* rename them;
* move them;
* delete them;
* preprocess in place;
* normalize them in place;
* rewrite them;
* add generated artifacts to raw dataset directories.

Generated/preprocessed material belongs only in roadmap-approved FedSIRA locations.

Ignore incomplete temporary/download artifacts such as:

* `.ongoing`;
* `.part`;
* `.tmp`;
* lock files;
* obviously incomplete transfers;

when establishing canonical data identity.

Do not mistake current download state for the canonical dataset definition.

# N-BAIOT CONTRACT

For N-BaIoT:

* use the roadmap-defined physical/domain proxies;
* use the canonical class vocabulary;
* respect the roadmap's feature-count/schema expectations;
* respect roadmap role intervals and evidence boundaries;
* enforce finite/missing-value policies exactly;
* preserve deterministic sample identity;
* validate target-holder/evidence feasibility rules;
* enforce supported/target isolation;
* enforce leakage rules;
* keep raw source files immutable.

Any path-to-label or path-to-device semantics must be explicit and tested.

Do not silently derive class meaning from arbitrary traversal order.

# CICIOT2023 CONTRACT

For CICIoT2023:

* use the roadmap-defined secondary-dataset role;
* inspect official CSV schema where required;
* derive/validate the canonical predictor schema;
* enforce canonical labels and target semantics;
* enforce non-predictive identifier exclusions;
* implement the roadmap-defined deterministic pseudo-domain construction;
* enforce role, leakage, target, and evidence restrictions;
* keep raw source files immutable.

Do not represent pseudo-domains as physical IoT devices if the roadmap does not.

Do not introduce claims stronger than the dataset/client construction supports.

# REAL-DATA SCHEMA AUDITS

Whenever an issue depends on concrete dataset properties:

1. read the roadmap;
2. inspect existing implementation/config;
3. inspect completed real dataset files non-destructively where available;
4. consult official documentation when required;
5. compare real schema against production assumptions;
6. implement explicit validation;
7. add automated contract tests.

Malformed or unsupported schemas must fail clearly.

The implementation must not silently adapt critical scientific meaning based on accidental file contents.

# ARCHITECTURE TESTS ARE A TOP PRIORITY

The architecture-test system is one of the **highest-priority deliverables in FedSIRA**.

A large portion may already exist from previous Milestone 1 work.

Therefore:

1. audit the existing architecture suite first;
2. preserve strong existing checks;
3. identify blind spots;
4. strengthen the suite immediately where required;
5. keep it active throughout every later issue.

Do not replace an already-good architecture system merely to build your own.

Do not postpone missing architecture enforcement until the end.

The objective is an **EXHAUSTIVE EXECUTABLE ARCHITECTURE CONSTITUTION** for FedSIRA.

Architecture tests must capture **EVERYTHING that can reasonably be detected automatically** from:

* repository agent instructions;
* `docs/Roadmap.md`;
* live GitHub acceptance criteria;
* project configuration;
* package boundaries;
* dependency direction;
* type contracts;
* scientific contracts;
* dataset contracts;
* role/evidence isolation;
* experiment contracts;
* CLI contracts;
* filesystem contracts;
* outputs/results contracts;
* provenance rules;
* reproducibility rules;
* naming rules;
* test architecture;
* issue-specific invariants.

# EXTRACT FEDSIRA-SPECIFIC ARCHITECTURE RULES

Do not build only generic Python architecture checks.

Systematically extract every mechanically enforceable FedSIRA rule from the roadmap.

Where mechanically testable, enforce concepts such as:

* package/module ownership;
* supported vs target information boundaries;
* role intervals and guard gaps;
* deterministic sample identity;
* domain identity;
* target-holder eligibility;
* scaling ownership and fit-data restrictions;
* scientific configuration ownership;
* capability/evidence isolation;
* experiment registration;
* dependency validity;
* artifact invalidation;
* provenance;
* claim-state derivation;
* deterministic execution;
* output/result separation;
* public CLI restrictions;
* reproducibility;
* reporting ownership.

Use the roadmap itself to discover the complete set.

A future developer should not be able to violate a deterministic rule simply because nobody remembered to review it manually.

# ARCHITECTURE TESTS MUST BE AGGRESSIVE

Where applicable, detect:

* forbidden imports;
* reverse dependencies;
* package-layer violations;
* cycles;
* wrong-module ownership;
* cross-domain leakage;
* public APIs exposing internals;
* primitive leakage where typed domain/config models are required;
* raw protocol strings;
* inappropriate `Any`;
* untyped public boundaries;
* generic `dict` structures where explicit models are required;
* hidden scientific constants;
* magic numbers;
* duplicate constants;
* YAML/config drift;
* configuration declared but unused;
* scientific configuration consumed but not canonically declared;
* unsupported enum values;
* mutable scientific globals;
* implicit defaults;
* silent fallbacks;
* compatibility shims;
* redirects;
* legacy aliases;
* stale project names;
* obsolete modules;
* duplicate canonical implementations;
* bypasses of canonical services;
* unreachable registry entries;
* unregistered implementations;
* invalid experiment identities;
* invalid experiment dependencies;
* unauthorized CLI commands;
* missing required CLI commands;
* CLI handlers bypassing canonical services;
* filesystem writes outside approved locations;
* computational reads from manuscript-facing `results/`;
* intermediates written into `results/`;
* manuscript exports improperly owned by `outputs/`;
* missing provenance;
* test-controlled scientific constants;
* uncontrolled randomness;
* inconsistent seeds;
* insecure/unsupported serialization;
* raw dataset mutation;
* preprocessing inside raw storage;
* production imports from tests;
* unsupported dataset assumptions;
* schema drift;
* label drift;
* domain/client identity drift;
* role leakage;
* target/support leakage;
* temporal leakage where applicable;
* train/evidence/report leakage;
* experiment matrix/config drift;
* invalid statistical pairing;
* evidence without provenance;
* forbidden generated Markdown;
* repository-root pollution;
* temporary artifacts;
* architecture bypass wrappers.

This is a minimum mindset, not a complete list.

# DEFENSE IN DEPTH

Use every repository/roadmap-required tool.

Where appropriate combine:

1. import/dependency architecture tests;
2. AST analysis;
3. runtime/reflection checks;
4. static typing;
5. schema validation;
6. configuration validation;
7. filesystem/layout scans;
8. registry consistency tests;
9. dataset-contract tests;
10. CLI-surface tests;
11. artifact/provenance tests;
12. Ruff;
13. formatter checks;
14. Pyright;
15. Pylance-compatible typing validation;
16. unit tests;
17. Hypothesis/property-based tests;
18. integration tests;
19. end-to-end tests;
20. numerical/scientific oracle tests;
21. negative/adversarial tests.

If a roadmap or issue names a dedicated library for a check, **USE IT**.

Do not replace a purpose-built library with a weaker regex shortcut merely because the shortcut is faster to write.

# ARCHITECTURE TESTS MUST BE DISCOVERY-BASED

Do not hardcode today's filenames as the architecture boundary unless the roadmap explicitly requires an exact path.

Wherever possible dynamically discover:

* production modules;
* packages;
* dataset adapters;
* configuration files;
* experiment implementations;
* registries;
* CLI commands;
* dependency edges;
* output/result readers and writers;
* artifact-producing modules;
* scientific constants.

A violating module added tomorrow should fail automatically.

# TEST THE ARCHITECTURE TESTS

Important architecture checks must themselves be proven effective.

Where practical provide:

* valid fixtures/examples;
* deliberately invalid fixtures/examples.

A test named after an architectural rule is insufficient if its checking implementation cannot actually detect the violation.

# ISSUE-BY-ISSUE EXECUTION CONTRACT

For **EVERY remaining or questionable GitHub issue**, complete the lifecycle below.

## 1. Refresh the Live Issue

Immediately before work, retrieve the issue from GitHub.

Read:

* complete title;
* complete body;
* milestone;
* labels;
* dependencies;
* checklist;
* acceptance criteria;
* quality gates;
* roadmap references;
* relevant comments.

Do not work from memory.

## 2. Map the Issue to `docs/Roadmap.md`

Find all relevant roadmap sections.

GitHub defines the work queue.

The roadmap defines **scientific and architectural correctness**.

## 3. Audit Existing Implementation BEFORE Editing

Determine:

* what already exists;
* what is already correct;
* what is partial;
* what is missing;
* what is wrong;
* what is duplicated;
* what violates the roadmap;
* what violates architecture;
* what tests already cover;
* what acceptance criteria are already demonstrably satisfied.

**This step is especially important for Milestone 1.**

Preserve legitimate correct work.

Prefer surgical continuation/fixes over unnecessary rewrites.

## 4. Implement the ENTIRE Remaining Issue Scope

Do not leave:

* TODOs;
* placeholders;
* fake implementations;
* empty stubs;
* temporary shortcuts;
* skipped scientific behavior;
* hardcoded expected outputs;
* test-only production behavior;
* unvalidated assumptions;
* requirements deferred to “future work.”

If the acceptance criterion belongs to the issue, finish it.

## 5. Add/Strengthen Tests WITH the Implementation

Use all applicable levels:

* unit;
* architecture;
* configuration;
* schema;
* property-based;
* regression;
* contract;
* integration;
* end-to-end;
* CLI;
* filesystem;
* artifact;
* provenance;
* numerical oracle;
* deterministic/reproducibility;
* negative/adversarial;
* real-data schema.

# QUALITY ENFORCEMENT AFTER EVERY ISSUE

After every issue, run all applicable configured gates, including:

* formatting verification;
* Ruff;
* Pyright;
* Pylance-compatible/static typing checks;
* architecture tests;
* unit tests;
* issue-specific tests;
* affected integration tests;
* affected end-to-end tests.

If these checks belong in nox, Makefile, CI, or equivalent project tooling according to the roadmap, ensure they are represented there.

Do not continue to another issue while the current issue leaves applicable gates failing.

# ISSUE-LEVEL HOSTILE AUDIT BEFORE COMMIT

Before committing, audit the issue from zero against:

* every acceptance criterion;
* every checklist item;
* relevant roadmap requirements;
* repository instructions;
* architecture;
* typing;
* configuration;
* dataset semantics;
* scientific correctness;
* numerical correctness;
* reproducibility;
* provenance;
* outputs/results;
* tests.

Fix all deficiencies first.

Passing tests alone is not evidence that every criterion is satisfied.

# COMMIT EACH COMPLETED ISSUE

When the issue is genuinely complete:

* inspect `git status`;
* ensure no scratch files remain;
* ensure unrelated pre-existing user work is not staged;
* stage only the intended changes;
* create a clear issue-specific commit;
* reference the GitHub issue where appropriate.

Do not bundle unrelated unfinished issues into one commit.

If an issue was already completely committed in a prior agent cycle, do **not** generate an empty or artificial duplicate commit.

# PUSH IMMEDIATELY

After the issue-specific commit:

* push;
* verify push success;
* verify intended branch;
* verify local/remote synchronization.

# POST-PUSH ACCEPTANCE AUDIT

After pushing, retrieve the live GitHub issue **again**.

Audit every criterion against the pushed repository state.

If anything remains missing:

**DO NOT CLOSE THE ISSUE.**

Fix it.

Rerun the required suite.

Commit the correction.

Push.

Refresh GitHub.

Audit again.

Repeat until clean.

# GITHUB CHECKLISTS

Check acceptance/checklist items only when the requirement has actually been demonstrated.

Do not mark items complete simply because relevant-looking code exists.

# CLOSE THE ISSUE

Close only when:

* implementation is complete;
* roadmap is satisfied;
* repository instructions are satisfied;
* acceptance criteria are demonstrated;
* checklist is accurate;
* architecture is clean;
* typing is clean;
* Ruff is clean;
* formatting is clean;
* relevant tests pass;
* changes are committed;
* changes are pushed;
* remote state is verified.

Then begin the next dependency-valid issue.

# MILESTONE COMPLETION CONTRACT

After all issues for a milestone are completed:

**DO NOT immediately move to the next milestone.**

## 1. Refresh the Milestone

Verify from live GitHub:

* intended issues are closed;
* no issue was omitted;
* no relevant new issue appeared;
* dependencies are satisfied;
* checklists reflect reality.

## 2. Perform a Milestone-Wide Hostile Audit

Look for:

* integration regressions;
* cross-issue contradictions;
* duplicate canonical implementations;
* architecture drift;
* stale modules;
* dead infrastructure;
* later changes invalidating earlier criteria;
* missing cross-cutting tests;
* configuration composition defects;
* dataset-contract drift;
* role/evidence leakage;
* scientific inconsistencies;
* mathematical inconsistencies;
* statistical inconsistencies;
* CLI inconsistencies;
* artifact/provenance defects;
* output/result violations;
* reproducibility gaps.

## 3. Fix Everything

Do not merely report the findings.

Fix them.

Run the complete applicable quality suite.

Commit milestone-audit corrections.

Push.

Repeat until clean.

## 4. Close the Milestone

Only close the GitHub milestone when the integrated milestone is genuinely complete.

# SONARQUBE HTTP API AUDIT AFTER EVERY MILESTONE

After each completed milestone, perform a full SonarQube cycle **before beginning the next milestone**.

Read SonarQube configuration/token from repository/environment evidence, including `.env` where applicable.

Never:

* print the token;
* echo it;
* expose it in logs;
* commit it;
* paste it into GitHub;
* write it into scratch documentation.

**USE THE SONARQUBE HTTP API DIRECTLY.**

**DO NOT SUBSTITUTE THE SONARQUBE CLI FOR THIS AUDIT.**

Determine server/project/branch identity from actual configuration.

Query applicable API endpoints for:

* bugs;
* vulnerabilities;
* security findings;
* reliability findings;
* maintainability findings;
* code smells;
* duplication;
* coverage/quality findings where applicable;
* quality gate;
* unresolved actionable findings.

Inspect the actual source behind each finding.

Prefer fixing code.

Do not game SonarQube by casually:

* suppressing findings;
* disabling rules;
* adding ignore comments;
* excluding source;
* lowering thresholds;
* marking valid issues false positive.

After fixes rerun:

* formatting;
* Ruff;
* Pyright;
* Pylance-compatible typing;
* architecture tests;
* unit tests;
* affected integration/e2e tests;
* applicable project quality gates.

Commit.

Push.

Re-query the API.

Repeat until no unresolved valid actionable findings remain.

# SCIENTIFIC CORRECTNESS IS MANDATORY

FedSIRA is a research repository.

Software correctness is not sufficient.

Every roadmap-defined mathematical, statistical, algorithmic, evidence-isolation, role, decision, or scientific invariant must be independently validated where practical.

Use techniques including:

* exact identities;
* independent numerical oracles;
* hand-solvable examples;
* exhaustive small cases;
* controlled synthetic datasets;
* high-precision references;
* independent reference implementations;
* property-based testing;
* boundary cases;
* invariance tests;
* deterministic pairing;
* role-leakage tests;
* client/domain-isolation tests;
* permutation tests where invariance is expected;
* negative controls;
* falsification tests.

Do not call an oracle independent if it merely copies production logic.

If a scientific procedure is unclear, research the primary source rather than guessing.

# DO NOT WEAKEN LEGITIMATE TESTS

When a legitimate test exposes a bug:

**FIX THE CODE.**

Do not:

* delete the assertion;
* loosen tolerances without scientific justification;
* skip the test;
* xfail a legitimate failure;
* shrink property domains merely to hide a bug;
* alter fixtures to evade the defect;
* add unjustified architecture exclusions;
* hide modules from discovery;
* disable static rules.

If the test genuinely contradicts the roadmap, correct the test using explicit roadmap/scientific evidence.

# KEEP THE REPOSITORY CLEAN CONTINUOUSLY

Remove obsolete implementation artifacts when discovered:

* dead code;
* duplicate code;
* obsolete shims;
* stale aliases;
* redirects;
* unused modules;
* commented-out implementations;
* debug output;
* abandoned configuration;
* scratch scripts;
* generated planning documents;
* agent notes;
* temporary files.

Do not preserve known garbage until the very end without a dependency reason.

# CONTINUOUS ROADMAP TRACEABILITY

Before significant design choices, internally ask:

> What does `docs/Roadmap.md` require?

Before closing each issue:

> Can every acceptance criterion be demonstrated, and does the implementation still preserve the complete FedSIRA contract?

Before closing each milestone:

> Does the integrated milestone still satisfy the roadmap and every applicable repository rule?

When uncertain, reread the authoritative source and research what remains unspecified.

Do not ask me.

# FINAL TICKET-BY-TICKET HOSTILE AUDIT

Closing the final open issue is **NOT completion**.

After all milestones are implemented, audited, closed, and SonarQube-audited:

Start again from live GitHub.

Go **ticket by ticket across the entire FedSIRA repository**, including issues completed before this agent cycle.

For every issue:

1. retrieve the final live issue;
2. reread the complete body;
3. reread relevant comments;
4. reread every acceptance criterion;
5. reread every checklist item;
6. map it to the final roadmap;
7. inspect final source;
8. inspect final tests;
9. inspect configuration;
10. inspect architecture;
11. inspect dataset handling;
12. inspect artifacts/runtime where applicable;
13. verify later milestones did not invalidate it.

Classify every acceptance criterion:

```text
DEMONSTRATED
or
DEFICIENT
```

If deficient:

* reopen/fix as appropriate;
* implement the correction;
* rerun validation;
* commit;
* push;
* update GitHub;
* close again only when legitimately satisfied.

Do not preserve an incorrect closed issue merely because a previous agent cycle marked it done.

# FINAL ARCHITECTURE HOSTILE AUDIT — TRY TO BREAK THE GUARDRAILS

Perform a dedicated architecture audit across the **ENTIRE repository**.

Act as a hostile future developer attempting to bypass the tests.

Look for blind spots including:

* scans restricted to known files;
* new packages escaping checks;
* semantic violations missed by name-only rules;
* regex where AST is required;
* config values without consumer traceability;
* implementations escaping registry checks;
* dynamic imports escaping dependency checks;
* reverse dependencies not tested;
* nested paths escaping filesystem scans;
* unjustified exclusions;
* dataset adapters not auto-discovered;
* CLI commands not automatically detected;
* experiments not automatically detected;
* output/result consumers not automatically discovered;
* scientific constants hidden indirectly;
* environment-variable bypasses;
* import aliases evading rules;
* type aliases reintroducing primitive leakage;
* wrappers bypassing canonical validation;
* raw-data mutation paths;
* role/evidence isolation bypasses;
* assumptions derived from incomplete real datasets.

Strengthen every discovered blind spot.

The architecture suite must function as an:

**EXECUTABLE FEDSIRA REPOSITORY CONSTITUTION.**

The target is:

> Any mechanically detectable violation of repository instructions, `docs/Roadmap.md`, or canonical FedSIRA architecture should fail automatically as close as possible to when the violation is introduced.

# FINAL REAL-DATA CONTRACT AUDIT

Before completion, perform a dedicated audit of every roadmap-required dataset.

Verify:

* canonical dataset identities;
* authoritative schemas;
* label mappings;
* class order;
* target semantics;
* domain/client identities;
* role intervals;
* deterministic sample identity;
* scaling fit boundaries;
* malformed schemas fail clearly;
* no accidental file-order dependence;
* no unjustified hardcoded snapshot counts;
* incomplete local samples are not mistaken for full datasets;
* raw data remains immutable;
* preprocessing writes only to approved locations;
* supported/target evidence isolation is preserved;
* no forbidden cross-domain leakage exists;
* tests protect actual production contracts.

Where completed real files exist, perform non-mutating schema sanity checks.

Where local evidence is incomplete, consult official documentation/primary sources instead of guessing.

Do not block the entire repository on unrelated dataset-transfer progress if the production contract can be correctly implemented and validated against authoritative evidence.

# FINAL QUALITY CYCLE

Run the complete configured validation suite, including all applicable:

* formatter checks;
* Ruff;
* Pyright;
* Pylance-compatible static checks;
* architecture tests;
* unit tests;
* property-based tests;
* configuration tests;
* schema tests;
* integration tests;
* end-to-end tests;
* scientific verification tests;
* CLI tests;
* dataset-contract tests;
* artifact tests;
* provenance tests;
* reproducibility tests.

Fix all failures.

Do not waive legitimate failures.

# FINAL SONARQUBE API AUDIT

Run a final complete SonarQube **HTTP API** audit.

Inspect all remaining actionable:

* bugs;
* vulnerabilities;
* security findings;
* reliability findings;
* maintainability findings;
* code smells;
* duplication;
* quality-gate findings;
* applicable coverage findings.

Fix every valid actionable finding.

Rerun the full quality suite.

Commit.

Push.

Re-query SonarQube.

Repeat until clean.

# FINAL REPOSITORY VERIFICATION

Before declaring completion verify:

* working tree clean;
* correct branch;
* branch synchronized with remote;
* every intended commit pushed;
* no `docs/temp/`;
* no agent scratch files;
* no accidental planning Markdown;
* no accidental root files;
* no uncommitted implementation;
* no secrets committed;
* no raw dataset modifications;
* all intended GitHub issues legitimately closed;
* all intended GitHub milestones legitimately closed;
* all acceptance criteria demonstrably satisfied;
* all FedSIRA roadmap requirements implemented;
* all applicable repository instructions respected;
* architecture suite hostile-audited;
* real-data contracts hostile-audited;
* full quality suite clean;
* final SonarQube HTTP API audit clean of valid actionable findings.

# COMPLETION DEFINITION

You are **NOT done** because:

* the existing Milestone 1 work looked substantial;
* Milestone 1 is complete;
* several milestones are complete;
* all code has been written;
* tests happen to pass;
* all open issues were closed once;
* the final milestone was reached;
* SonarQube was queried once;
* architecture tests exist;
* a partial dataset run works;
* you produced a list of remaining problems.

You are done only when:

```text
CURRENT STATE FULLY RECONCILED
AND
ALL legitimate prior work preserved
AND
ALL remaining milestones implemented
AND
ALL intended issues implemented
AND
EVERY issue individually audited
AND
EVERY acceptance criterion demonstrated
AND
EVERY required issue change committed and pushed
AND
EVERY issue legitimately closed
AND
EVERY milestone integration-audited
AND
EVERY milestone legitimately closed
AND
SonarQube HTTP API audited after each completed milestone
AND
valid actionable SonarQube findings fixed
AND
final ticket-by-ticket hostile audit passes
AND
final architecture hostile audit passes
AND
final real-data contract audit passes
AND
final complete quality suite passes
AND
final SonarQube API audit passes
AND
repository is clean and synchronized
```

Do not stop because an ambiguity appears.

Research it.

Do not stop because a number is missing.

Find the strongest authoritative evidence.

Do not stop because documentation is unclear.

Read the roadmap, GitHub discussion, tests, history, primary source, official documentation, and reference implementation and choose the best defensible interpretation.

Do not restart completed work simply because you do not know the current progress yet.

**Audit first. Preserve what is correct. Resume what is incomplete.**

Do not stop because I am unavailable.

**I am intentionally unavailable. You are expected to exercise expert engineering and scientific judgment and autonomously resume FedSIRA from its exact current state, finish whatever remains of Milestone 1, and continue through every subsequent milestone until the entire repository is fully implemented, audited, pushed, closed, synchronized, and verified.**
