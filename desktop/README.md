# CodeSaver Desktop

Desktop application source for CodeSaver Desktop 1.9.0.

The current desktop tools include:

- selected-archive CRC checks, glob-based member filtering, and safe extraction of a single file;
- detailed comparison JSON export and per-member compression savings reports;
- duplicate-content, symlink, permission, timestamp-range, and large-member audits for selected ZIPs;
- repeated-name, case-collision, encryption, compression-method, and high-expansion-ratio checks;
- portability, Unicode normalization, path-depth, symlink-target, and file/directory conflict audits;
- nested ZIP discovery, ZIP64 and data-descriptor inspection, trailing-data detection, and central-directory signature checks;

- comparing two ZIP archives and summarizing added, removed, and changed files;
- exporting SHA-256 hashes for archive members as CSV;
- inspecting the unpacked size of an archive;
- previewing retention cleanup before removing old backups;
- copying an archive manifest as JSON.
- filtering the archive list by a 7-, 30-, or 90-day date window;
- previewing a selected archive's date, size, and file count;
- switching between compact and comfortable archive-list density.
- pinning important archives persistently and comparing a snapshot with the preceding backup.
- restoring a whole archive or chosen files into a separate folder without replacing files already there.
- adding archive labels and notes, filtering by labels, searching annotations, and exporting a portable catalog.
- reviewing file additions, modifications, and removals across consecutive backups with live path filtering and CSV export;
- selecting the warm autumn theme or disabling CodeSaver's custom styling independently.

The project comparison window now shows a searchable results table, status counts and filters, supports CSV export, and lets you copy a path or open its location.

The application uses the shared CodeSaver backup engine and PyQt5. Build and
platform packaging instructions are available in the repository documentation.

See the [Desktop 1.8.0 release notes](../docs/releases/desktop-v1.8.0.md).

Desktop 1.9.0 adds named backup profiles interchangeable with the CLI. See the [release notes](../docs/releases/desktop-v1.9.0.md).
