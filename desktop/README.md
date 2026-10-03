# CodeSaver Desktop

Desktop application source for CodeSaver Desktop 1.6.8.

The current desktop tools include:

- selected-archive CRC checks, glob-based member filtering, and safe extraction of a single file;
- detailed comparison JSON export and per-member compression savings reports;
- duplicate-content, symlink, permission, timestamp-range, and large-member audits for selected ZIPs;
- repeated-name, case-collision, encryption, compression-method, and high-expansion-ratio checks;
- portability, Unicode normalization, path-depth, symlink-target, and file/directory conflict audits;

- comparing two ZIP archives and summarizing added, removed, and changed files;
- exporting SHA-256 hashes for archive members as CSV;
- inspecting the unpacked size of an archive;
- previewing retention cleanup before removing old backups;
- copying an archive manifest as JSON.

The application uses the shared CodeSaver backup engine and PyQt5. Build and
platform packaging instructions are available in the repository documentation.
