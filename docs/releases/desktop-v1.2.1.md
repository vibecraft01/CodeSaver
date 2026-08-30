# CodeSaver Desktop v1.2.1

## Highlights

- Added CSV file-inventory export with relative path, byte size, and modification time.
- Added an exclusion-rules viewer for auditing what will be skipped.
- Added symbolic-link scanning to identify unusual project filesystem entries.
- Added one-click copying of the current Git context as JSON.
- Added direct access to the Desktop configuration file.
- Added opt-in upload of a selected ZIP archive to a configured cloud endpoint.
- Cloud credentials are read from `CODESAVER_CLOUD_TOKEN`; local restore remains fully offline.

## Validation

- 46 tests passed locally.
- Black and Flake8 passed.
- Windows Desktop executable build completed successfully.
