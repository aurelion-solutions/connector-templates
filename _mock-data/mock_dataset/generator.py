"""Deterministic mock company dataset → SQLite INSERT script.

Fixed seed → reproducible persons, employments, accounts, roles, privileges,
and account–role / account–privilege links. All personal data is synthetic.
"""

from __future__ import annotations

import random
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

DATASET_SEED = 42

_NS = uuid.UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479')


def _eid(kind: str, n: int) -> str:
    return str(uuid.uuid5(_NS, f'{kind}:{n}'))


def _sql_str(value: object | None) -> str:
    if value is None:
        return 'NULL'
    s = str(value).replace("'", "''")
    return f"'{s}'"


def _sql_int(b: bool | int) -> str:
    if isinstance(b, bool):
        return '1' if b else '0'
    return str(int(b))


@dataclass(frozen=True)
class ExpectedCounts:
    persons: int
    employments: int
    accounts: int
    roles: int
    privileges: int


def expected_counts() -> ExpectedCounts:
    return ExpectedCounts(
        persons=400,
        employments=450,
        accounts=400,
        roles=30,
        privileges=100,
    )


FIRST_NAMES = (
    'Kai', 'Morgan', 'Riley', 'Quinn', 'Avery', 'Jordan', 'Casey', 'Skyler',
    'Drew', 'Reese', 'Rowan', 'Emerson', 'Hayden', 'Parker', 'Sage', 'River',
    'Phoenix', 'Eden', 'Blair', 'Cameron', 'Logan', 'Taylor', 'Jamie', 'Alex',
    'Sam', 'Charlie', 'Finley', 'Harper', 'Marlowe', 'Ellis', 'Remy', 'Shay',
)

LAST_NAMES = (
    'Ashford', 'Bennett', 'Caldwell', 'Donovan', 'Ellsworth', 'Fletcher',
    'Grayson', 'Hollis', 'Iverson', 'Kensington', 'Langford', 'Mercer',
    'Northrop', 'Prescott', 'Quinlan', 'Redfield', 'Sterling', 'Thackeray',
    'Underwood', 'Vance', 'Whitaker', 'Yardley', 'Zimmerman', 'Blackwood',
    'Carmichael', 'Davenport', 'Eastman', 'Fairchild', 'Goldwyn', 'Harrington',
)

CITIES = (
    'Riverside', 'Maple Grove', 'Cedar Falls', 'Willow Creek', 'Stonebridge',
    'Lakeview', 'Highland Park', 'Fairmont', 'Brookhaven', 'Summit Ridge',
    'Northfield', 'Westport', 'Easton', 'Southbay', 'Millbrook', 'Ashford',
    'Clearwater', 'Redwood', 'Silverton', 'Greenwich', 'Oakhaven', 'Pinehurst',
)

TIMEZONES = (
    'America/Chicago', 'America/New_York', 'America/Denver', 'America/Los_Angeles',
    'America/Phoenix', 'America/Toronto', 'UTC',
)

ROLE_TYPES = (
    ('business',) * 8
    + ('technical',) * 10
    + ('admin',) * 5
    + ('approver',) * 4
    + ('manager',) * 3
)

PRIV_TYPES = (
    ('application',) * 35
    + ('data',) * 25
    + ('system',) * 20
    + ('compliance',) * 12
    + ('integration',) * 8
)

PRIV_NAMESPACES = (
    'iam', 'hris', 'finance', 'engineering', 'sales', 'support', 'security',
    'analytics', 'infra', 'compliance',
)

ORG_SPECS: list[tuple[int, int | None, str]] = [
    (0, None, 'Executive Office'),
    (1, 0, 'Engineering'),
    (2, 0, 'Product'),
    (3, 0, 'Operations'),
    (4, 1, 'Platform'),
    (5, 1, 'Applications'),
    (6, 1, 'Security Engineering'),
    (7, 2, 'Product Management'),
    (8, 2, 'Design'),
    (9, 3, 'Customer Success'),
    (10, 3, 'IT Operations'),
    (11, 5, 'Integrations'),
    (12, 9, 'Professional Services'),
    (13, 10, 'Service Desk'),
]

TITLE_NAMES = [
    'Analyst I', 'Analyst II', 'Senior Analyst', 'Consultant', 'Senior Consultant',
    'Engineer I', 'Engineer II', 'Senior Engineer', 'Staff Engineer', 'Principal Engineer',
    'Engineering Manager', 'Director Engineering', 'Product Manager', 'Senior PM',
    'Designer', 'Senior Designer', 'Support Specialist', 'Support Lead',
    'Account Manager', 'Solutions Architect', 'Security Engineer', 'IT Administrator',
    'DevOps Engineer', 'Data Engineer', 'QA Engineer', 'Scrum Master', 'Tech Writer',
    'Finance Partner', 'HR Partner',
]

EMP_TYPES = ('full_time', 'part_time', 'contractor', 'bench')


def build_sql(*, seed: int = DATASET_SEED) -> str:
    rng = random.Random(seed)
    lines: list[str] = [
        '-- Synthetic mock dataset for Aurelion mock connector.',
        '-- Regenerate: cd _mock-data && python -m mock_dataset',
        'PRAGMA foreign_keys = OFF;',
    ]

    company_id = _eid('company', 0)
    for tbl in (
        'account_privileges',
        'account_roles',
        'accounts',
        'employments',
        'persons',
        'privileges',
        'roles',
        'job_titles',
        'org_units',
        'companies',
    ):
        lines.append(f'DELETE FROM {tbl};')

    lines.append(
        f'INSERT INTO companies (id, name) VALUES ({_sql_str(company_id)}, '
        f'{_sql_str("Aurion Mock Corporation (synthetic)")});',
    )

    org_ids: dict[int, str] = {}
    for idx, parent_idx, name in ORG_SPECS:
        oid = _eid('org', idx)
        org_ids[idx] = oid
        parent_sql = 'NULL' if parent_idx is None else _sql_str(org_ids[parent_idx])
        lines.append(
            'INSERT INTO org_units (id, company_id, parent_org_unit_id, name) VALUES ('
            f'{_sql_str(oid)}, {_sql_str(company_id)}, {parent_sql}, {_sql_str(name)});',
        )

    title_ids: dict[int, str] = {}
    for ti, tname in enumerate(TITLE_NAMES):
        tid = _eid('title', ti)
        title_ids[ti] = tid
        lines.append(
            f'INSERT INTO job_titles (id, name) VALUES ({_sql_str(tid)}, {_sql_str(tname)});',
        )

    role_ids: list[str] = []
    for ri in range(30):
        rid = _eid('role', ri)
        role_ids.append(rid)
        rtype = ROLE_TYPES[ri]
        name = f'{rtype.upper()}_{ri + 1:02d}_{rng.choice("ACEIKMNORT")}{rng.choice("ACEIKMNORT")}'
        lines.append(
            f'INSERT INTO roles (id, name, display_name, type, is_active) VALUES ('
            f'{_sql_str(rid)}, {_sql_str(name)}, {_sql_str(name.replace("_", " "))}, '
            f'{_sql_str(rtype)}, 1);',
        )

    priv_ids: list[str] = []
    for pi in range(100):
        prid = _eid('priv', pi)
        priv_ids.append(prid)
        ptype = PRIV_TYPES[pi]
        ns = PRIV_NAMESPACES[pi % len(PRIV_NAMESPACES)]
        pname = f'{ns}.{ptype}.{pi + 1:03d}'
        lines.append(
            'INSERT INTO privileges (id, name, display_name, type, namespace, is_active) VALUES ('
            f'{_sql_str(prid)}, {_sql_str(pname)}, {_sql_str(pname.replace(".", " ").title())}, '
            f'{_sql_str(ptype)}, {_sql_str(ns)}, 1);',
        )

    base = datetime(1990, 1, 1, tzinfo=UTC)
    person_ids: list[str] = []
    for pi in range(400):
        pid = _eid('person', pi)
        person_ids.append(pid)
        fn = FIRST_NAMES[pi % len(FIRST_NAMES)]
        ln = LAST_NAMES[(pi * 7) % len(LAST_NAMES)]
        full_name = f'{fn} {ln}'
        slug = f'{fn.lower()}.{ln.lower()}.{pi}'
        email = f'{slug}@mock.aurion.example'
        city = CITIES[(pi * 3) % len(CITIES)]
        phone = f'+1-555-01{pi % 100:02d}-{pi % 10000:04d}'
        tz = TIMEZONES[pi % len(TIMEZONES)]
        ssn = f'FAKE-SSN-{pi:03d}-{pi * 11 % 10000:04d}'
        dob = (base + timedelta(days=(pi * 97) % 12000)).date().isoformat()
        ou = org_ids[pi % len(ORG_SPECS)]
        jt = title_ids[pi % len(TITLE_NAMES)]
        lines.append(
            'INSERT INTO persons (id, full_name, email, city, phone, timezone, '
            'synthetic_ssn, synthetic_dob, primary_org_unit_id, primary_title_id) VALUES ('
            f'{_sql_str(pid)}, {_sql_str(full_name)}, {_sql_str(email)}, {_sql_str(city)}, '
            f'{_sql_str(phone)}, {_sql_str(tz)}, {_sql_str(ssn)}, {_sql_str(dob)}, '
            f'{_sql_str(ou)}, {_sql_str(jt)});',
        )

    perm = list(range(400))
    rng.shuffle(perm)
    no_emp = set(perm[:5])
    two_emp = set(perm[5:60])
    emp_key = 0

    def emit_employment(
        pidx: int,
        etype: str,
        status: str,
        ended: str | None,
    ) -> None:
        nonlocal emp_key
        eid_ = _eid('employment', emp_key)
        emp_key += 1
        pid = person_ids[pidx]
        ou = org_ids[(pidx + sum(ord(c) for c in etype)) % len(ORG_SPECS)]
        jt = title_ids[(pidx * 2) % len(TITLE_NAMES)]
        started = (base + timedelta(days=500 + (pidx * 13) % 4000)).date().isoformat()
        lines.append(
            'INSERT INTO employments (id, person_id, employment_type, status, started_at, '
            'ended_at, org_unit_id, job_title_id) VALUES ('
            f'{_sql_str(eid_)}, {_sql_str(pid)}, {_sql_str(etype)}, {_sql_str(status)}, '
            f'{_sql_str(started)}, {(_sql_str(ended) if ended else "NULL")}, '
            f'{_sql_str(ou)}, {_sql_str(jt)});',
        )

    for pi in range(400):
        if pi in no_emp:
            continue
        count = 2 if pi in two_emp else 1
        for j in range(count):
            et = EMP_TYPES[(pi + j) % len(EMP_TYPES)]
            if et == 'bench' and rng.random() < 0.35:
                status = 'inactive'
                ended = (base + timedelta(days=2000 + pi + j)).date().isoformat()
            else:
                status = 'active'
                ended = None
            emit_employment(pi, et, status, ended)

    assert emp_key == 450, f'expected 450 employments, got {emp_key}'

    perm_a = list(range(400))
    rng.shuffle(perm_a)
    no_acct = set(perm_a[:20])
    two_acct = set(perm_a[20:40])
    account_ids: list[str] = []
    account_flags: list[tuple[bool, bool, int | None]] = []

    ai = 0
    for pi in range(400):
        if pi in no_acct:
            continue
        slots = 2 if pi in two_acct else 1
        for s in range(slots):
            aid = _eid('account', ai)
            account_ids.append(aid)
            ai += 1
            p = person_ids[pi]
            uname = f'u{pi}.{s}'
            email = f'{uname}@mock.aurion.example'
            display = f'Account {pi}-{s}'
            is_priv = rng.random() < 0.12 or pi in two_acct
            is_svc = rng.random() < 0.03
            mfa = rng.random() < 0.55
            auth_local = rng.random() < 0.85
            is_active = rng.random() < 0.94
            ns = rng.choice(('corp', 'corp', 'corp', 'vendors', 'labs'))
            pwd_at = (base + timedelta(days=100 + ai)).isoformat()
            login_at = (
                (base + timedelta(days=50 + ai * 3)).isoformat()
                if is_active and rng.random() < 0.8
                else None
            )
            account_flags.append((is_priv, is_svc, pi))
            lines.append(
                'INSERT INTO accounts (id, person_id, username, email, display_name, is_active, '
                'is_mfa_on, is_privileged, is_service, auth_local, password_updated_at, '
                'last_successful_login, namespace) VALUES ('
                f'{_sql_str(aid)}, {_sql_str(p)}, {_sql_str(uname)}, {_sql_str(email)}, '
                f'{_sql_str(display)}, {_sql_int(is_active)}, {_sql_int(mfa)}, {_sql_int(is_priv)}, '
                f'{_sql_int(is_svc)}, {_sql_int(auth_local)}, {_sql_str(pwd_at)}, '
                f'{_sql_str(login_at) if login_at else "NULL"}, {_sql_str(ns)});',
            )

    assert len(account_ids) == 400, f'expected 400 accounts, got {len(account_ids)}'

    ar_count = 0
    ap_count = 0
    for idx, aid in enumerate(account_ids):
        is_priv, is_svc, pidx = account_flags[idx]
        weight = 1.0
        if is_priv:
            weight += 2.2
        if is_svc:
            weight += 1.5
        if pidx is not None and pidx in two_acct:
            weight += 0.4
        n_roles = max(1, min(12, int(rng.triangular(1, 4, 2 + weight))))
        n_privs = max(1, min(25, int(rng.triangular(2, 10, 4 + weight * 1.2))))
        rpick = rng.sample(role_ids, n_roles)
        ppick = rng.sample(priv_ids, n_privs)
        for rid in rpick:
            lines.append(
                'INSERT INTO account_roles (account_id, role_id) VALUES ('
                f'{_sql_str(aid)}, {_sql_str(rid)});',
            )
            ar_count += 1
        for prid in ppick:
            lines.append(
                'INSERT INTO account_privileges (account_id, privilege_id) VALUES ('
                f'{_sql_str(aid)}, {_sql_str(prid)});',
            )
            ap_count += 1

    lines.insert(
        2,
        f'-- persons=400 employments=450 accounts=400 roles=30 privileges=100 '
        f'account_roles={ar_count} account_privileges={ap_count}',
    )
    lines.append('PRAGMA foreign_keys = ON;')
    return '\n'.join(lines) + '\n'


def iter_statements(sql: str) -> Iterator[str]:
    buf: list[str] = []
    for line in sql.splitlines():
        s = line.strip()
        if not s or s.startswith('--'):
            continue
        buf.append(line)
        if s.endswith(';'):
            yield '\n'.join(buf).strip()
            buf = []
    if buf:
        yield '\n'.join(buf).strip()


def write_seed_sql(path: str) -> None:
    from pathlib import Path

    Path(path).write_text(build_sql(), encoding='utf-8')
