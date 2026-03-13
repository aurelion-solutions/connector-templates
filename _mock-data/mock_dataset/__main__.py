"""Write seed.sql next to this generator package (_mock-data/seed.sql)."""

from pathlib import Path

from mock_dataset.generator import write_seed_sql

if __name__ == '__main__':
    out = Path(__file__).resolve().parents[1] / 'seed.sql'
    write_seed_sql(str(out))
    print(f'Wrote {out}')
