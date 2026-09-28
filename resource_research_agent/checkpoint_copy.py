"""Copy-first codec migration/rollback. Never rewrite the source database."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
from .project_state import decode_project_state, encode_project_state
from .performance import measured


def copy_checkpoints(source, destination, *, compact):
    source=Path(source).expanduser().resolve(strict=True)
    destination=Path(destination).expanduser().absolute()
    if destination.exists() or source==destination:
        raise ValueError('Destination must be a new database file; the source is preserved')
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        handle=tempfile.NamedTemporaryFile(prefix='.scout-copy-',suffix='.sqlite3',dir=destination.parent,delete=False)
        temporary=Path(handle.name);handle.close()
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as original, closing(sqlite3.connect(temporary)) as copied, copied:
            with measured('checkpoint.database_backup'):original.backup(copied)
            converted=[]
            for table,field in [('scout_improvement_projects','state_json'),('scout_evidence_records','document')]:
                if not copied.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',('table',table)).fetchone():continue
                ids=[r[0] for r in copied.execute(f'SELECT id FROM {table}')]
                for ident in ids:
                    raw=copied.execute(f'SELECT {field} FROM {table} WHERE id=?',(ident,)).fetchone()[0]
                    state=decode_project_state(raw);encoded=encode_project_state(state,compact=compact)
                    if decode_project_state(encoded)!=state:raise ValueError('Checkpoint conversion changed content')
                    copied.execute(f'UPDATE {table} SET {field}=? WHERE id=?',(encoded,ident))
                    converted.append({'table':table,'id':ident,'beforeCharacters':len(raw),'afterCharacters':len(encoded)})
            if copied.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Copied database integrity failed')
            if copied.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Copied database reference check failed')
        # A no-clobber publication prevents a racing destination from being lost.
        os.link(temporary,destination)
        return {'source':str(source),'destination':str(destination),'codec':'compact' if compact else 'legacy',
                'sourceModified':False,'verified':True,'records':converted}
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
