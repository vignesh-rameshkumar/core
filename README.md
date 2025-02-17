## Agnikul Core ERP

Core ERP System for Agnikul Cosmos

### Custom Bench Commands

#### Backup App Command

```bash
bench backup-app [OPTIONS] APPNAME
```

Backup all documents for a specific app in the Frappe/ERPNext environment.

**Options:**
- `--site`: Specify the site name (optional)

**Example:**
```bash
bench backup-app core
bench backup-app core --site mysite
```

#### Restore App Command

```bash
bench restore-app [OPTIONS] APPNAME [BACKUP_PATH]
```

Restore documents for a specific app from a backup.

**Options:**
- `--site`: Specify the site name (optional)
- `--verbose`: Enable detailed logging for troubleshooting
- `BACKUP_PATH`: Optional path to a specific backup (if not provided, uses the most recent backup)

**Example:**
```bash
bench restore-app core
bench restore-app core --site mysite
bench restore-app core --verbose
bench restore-app core /path/to/specific/backup
```

#### Delete App Command

```bash
bench delete-app [OPTIONS] APPNAME
```

Delete all documents for a specific app.

**Options:**
- `--site`: Specify the site name (optional)
- `--backup/--no-backup`: Take a backup before deletion (default: yes)

**Example:**
```bash
bench delete-app core
bench delete-app core --site mysite
bench delete-app core --no-backup
```

#### Backup Doctype Command

```bash
bench backup-doctype [OPTIONS] DOCTYPE
```

Backup a specific Doctype within a given date range.

**Options:**
- `--site`: Specify the site name (optional)
- `--from`: Start date in YYYY-MM-DD format (optional)
- `--to`: End date in YYYY-MM-DD format (optional)

**Example:**
```bash
bench backup-doctype User --from 2025-01-01 --to 2025-01-31
bench backup-doctype User --from 2025-01-01 --to 2025-01-31 --site mysite
```

#### Restore Doctype Command

```bash
bench restore-doctype [OPTIONS] DOCTYPE [BACKUP_FILE]
```

Restore the latest backup or a specific backup file of a Doctype.

**Options:**
- `--site`: Specify the site name (optional)
- `BACKUP_FILE`: Optional name of the backup file to restore (if not provided, restores the latest backup)

**Example:**
```bash
bench restore-doctype User
bench restore-doctype User --site mysite
bench restore-doctype User User-20250217-160622.json
```

```bash
bench restore-doctype [OPTIONS] DOCTYPE
```

Restore the latest backup of a specific Doctype.

**Options:**
- `--site`: Specify the site name (optional)

**Example:**
```bash
bench restore-doctype User
bench restore-doctype User --site mysite
```

### Accessing Command Help Manual

You can access detailed help documentation for each custom command directly in the terminal using the following methods:

#### General Help for Custom Commands
```bash
bench --help
```

#### Specific Command Help

1. Backup App Command
```bash
bench backup-app --help
```

2. Restore App Command
```bash
bench restore-app --help
```

3. Delete App Command
```bash
bench delete-app --help
```

4. Backup Doctype Command
```bash
bench backup-doctype --help
```

5. Restore Doctype Command
```bash
bench restore-doctype --help
```

Each help command provides:
- Detailed description of the command
- Available options
- Usage examples
- Potential use cases
- Safety considerations

#### Additional CLI Help Tips
- Use `-h` as a shorthand for `--help`
- Example: `bench backup-app -h`
- Provides the same comprehensive documentation as `--help`

**Pro Tip**: Always review the help documentation before executing commands, especially for operations that modify your database.

#### License

MIT
