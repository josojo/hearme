-- Demo seed data for hearme v0.
--
-- Populates questions across three scopes (worldwide / continent / country),
-- envelopes with varied disclosed predicates, and matching aggregates so the
-- UI looks alive on first boot. Idempotent: ON CONFLICT DO NOTHING throughout.
--
-- Runs as the postgres superuser during docker-entrypoint-initdb.d execution
-- (alphabetical order, after 01-schema and 02-roles), so it can write to
-- broker-owned tables (envelopes, aggregates).

BEGIN;

-- A handful of distinct asker display rows.
WITH new_askers AS (
  INSERT INTO askers (id, display_name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Maya'),
    ('00000000-0000-0000-0000-000000000002', 'Hiroshi'),
    ('00000000-0000-0000-0000-000000000003', 'Sofia'),
    ('00000000-0000-0000-0000-000000000004', 'Lukas'),
    ('00000000-0000-0000-0000-000000000005', 'Aiyana'),
    ('00000000-0000-0000-0000-000000000006', 'Olamide'),
    ('00000000-0000-0000-0000-000000000007', 'Priya'),
    ('00000000-0000-0000-0000-000000000008', 'Nikolai'),
    ('00000000-0000-0000-0000-000000000009', 'Camila'),
    ('00000000-0000-0000-0000-00000000000a', 'Yuki'),
    ('00000000-0000-0000-0000-00000000000b', 'Anders'),
    ('00000000-0000-0000-0000-00000000000c', 'Fatima')
  ON CONFLICT (id) DO NOTHING
  RETURNING id
)
SELECT 1;

-- Demo questions across scopes.
-- Closes in 30 days so the seeded set stays "open" for a while.
INSERT INTO questions (id, asker_id, text, topic, scope, country, continent, closes_at) VALUES
  -- Worldwide
  ('10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    'Will AI agents make the open web more honest or more hostile?',
    'technology', 'worldwide', NULL, NULL,
    now() + interval '30 days'),
  ('10000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000002',
    'How many hours of deep work do you get on a typical day?',
    'work', 'worldwide', NULL, NULL,
    now() + interval '30 days'),
  ('10000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000003',
    'What is one habit that genuinely improved your life this year?',
    'life', 'worldwide', NULL, NULL,
    now() + interval '21 days'),
  ('10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000004',
    'If you could vote on a single global climate policy, what would it be?',
    'climate', 'worldwide', NULL, NULL,
    now() + interval '45 days'),
  ('10000000-0000-0000-0000-000000000005',
    '00000000-0000-0000-0000-000000000005',
    'Is remote work better, worse, or just different than office work?',
    'work', 'worldwide', NULL, NULL,
    now() + interval '30 days'),

  -- Continent: Europe
  ('20000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000004',
    'Should the EU require open-source AI for public services?',
    'policy', 'continent', NULL, 'EU',
    now() + interval '20 days'),
  ('20000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000008',
    'Has rail across Europe gotten meaningfully better in the last 5 years?',
    'travel', 'continent', NULL, 'EU',
    now() + interval '30 days'),

  -- Continent: North America
  ('20000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000005',
    'Is housing affordability a solvable problem in your city?',
    'housing', 'continent', NULL, 'NA',
    now() + interval '30 days'),
  ('20000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000001',
    'Should public transit be free at the point of use?',
    'transport', 'continent', NULL, 'NA',
    now() + interval '25 days'),

  -- Continent: Asia
  ('20000000-0000-0000-0000-000000000005',
    '00000000-0000-0000-0000-00000000000a',
    'Is the shift to mobile-first payments still accelerating, or saturating?',
    'fintech', 'continent', NULL, 'AS',
    now() + interval '30 days'),
  ('20000000-0000-0000-0000-000000000006',
    '00000000-0000-0000-0000-000000000007',
    'What is the most underrated city in Asia to live in right now?',
    'travel', 'continent', NULL, 'AS',
    now() + interval '40 days'),

  -- Continent: South America
  ('20000000-0000-0000-0000-000000000007',
    '00000000-0000-0000-0000-000000000009',
    'Is informal employment still the dominant reality across the region?',
    'economy', 'continent', NULL, 'SA',
    now() + interval '30 days'),

  -- Continent: Africa
  ('20000000-0000-0000-0000-000000000008',
    '00000000-0000-0000-0000-00000000000c',
    'Which sector will create the most jobs across the continent by 2030?',
    'economy', 'continent', NULL, 'AF',
    now() + interval '60 days'),

  -- Continent: Oceania
  ('20000000-0000-0000-0000-000000000009',
    '00000000-0000-0000-0000-000000000005',
    'Should there be a regional climate-migration framework?',
    'climate', 'continent', NULL, 'OC',
    now() + interval '45 days'),

  -- Country: United States
  ('30000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000005',
    'Should the U.S. raise the federal minimum wage above $15/hr?',
    'policy', 'country', 'US', 'NA',
    now() + interval '30 days'),
  ('30000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'Would you support replacing income tax with a land-value tax?',
    'policy', 'country', 'US', 'NA',
    now() + interval '40 days'),

  -- Country: Germany
  ('30000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000004',
    'Sollte das Deutschlandticket dauerhaft bei 49€ bleiben?',
    'transport', 'country', 'DE', 'EU',
    now() + interval '30 days'),
  ('30000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000004',
    'Brauchen wir mehr Mietpreisbremsen oder weniger Bauvorschriften?',
    'housing', 'country', 'DE', 'EU',
    now() + interval '30 days'),

  -- Country: Japan
  ('30000000-0000-0000-0000-000000000005',
    '00000000-0000-0000-0000-000000000002',
    'Has Japan''s push for English-medium tech jobs changed the hiring market?',
    'work', 'country', 'JP', 'AS',
    now() + interval '30 days'),
  ('30000000-0000-0000-0000-000000000006',
    '00000000-0000-0000-0000-00000000000a',
    'Will the four-day work week catch on outside trial companies?',
    'work', 'country', 'JP', 'AS',
    now() + interval '45 days'),

  -- Country: Brazil
  ('30000000-0000-0000-0000-000000000007',
    '00000000-0000-0000-0000-000000000003',
    'O Pix mudou permanentemente como você lida com dinheiro?',
    'fintech', 'country', 'BR', 'SA',
    now() + interval '30 days'),

  -- Country: India
  ('30000000-0000-0000-0000-000000000008',
    '00000000-0000-0000-0000-000000000007',
    'Will UPI volume still double in the next three years?',
    'fintech', 'country', 'IN', 'AS',
    now() + interval '35 days'),

  -- Country: United Kingdom
  ('30000000-0000-0000-0000-000000000009',
    '00000000-0000-0000-0000-000000000008',
    'Is the NHS reformable, or does it need a fundamentally different model?',
    'policy', 'country', 'GB', 'EU',
    now() + interval '30 days'),

  -- Country: Australia
  ('30000000-0000-0000-0000-00000000000a',
    '00000000-0000-0000-0000-000000000005',
    'Should the housing tax breaks for investors finally be wound back?',
    'housing', 'country', 'AU', 'OC',
    now() + interval '30 days'),

  -- Country: Nigeria
  ('30000000-0000-0000-0000-00000000000b',
    '00000000-0000-0000-0000-00000000000c',
    'Is the fuel-subsidy removal starting to pay off, or only hurting?',
    'economy', 'country', 'NG', 'AF',
    now() + interval '30 days'),

  -- Country: France
  ('30000000-0000-0000-0000-00000000000c',
    '00000000-0000-0000-0000-000000000004',
    'La semaine de 4 jours, est-ce viable dans le secteur public ?',
    'work', 'country', 'FR', 'EU',
    now() + interval '30 days')
ON CONFLICT (id) DO NOTHING;

-- Helper: insert a batch of envelopes for one question, then write the
-- matching aggregate row in one go. Each envelope gets a synthetic
-- agent_signature / delegation_hash — fine for demo, since the verifier
-- doesn't run against seeded data.
--
-- We use a CTE-per-question pattern so each block is self-contained.

-- Q1: AI agents
WITH env AS (
  INSERT INTO envelopes (question_id, unique_identifier, answer, disclosed_predicates, agent_signature, delegation_hash) VALUES
    ('10000000-0000-0000-0000-000000000001', 'seed-q1-u1', 'More honest — auditability finally beats virality.', '{"region":"EU","age_band":"25-34"}', 'sig-seed-1', 'del-seed-1'),
    ('10000000-0000-0000-0000-000000000001', 'seed-q1-u2', 'More hostile. Spam scales faster than trust.', '{"region":"NA","age_band":"35-44"}', 'sig-seed-2', 'del-seed-2'),
    ('10000000-0000-0000-0000-000000000001', 'seed-q1-u3', 'Both at once. Honest with the few, noisy with the many.', '{"region":"AS","age_band":"25-34"}', 'sig-seed-3', 'del-seed-3'),
    ('10000000-0000-0000-0000-000000000001', 'seed-q1-u4', 'Honest, eventually. The first 18 months will be ugly.', '{"region":"EU","age_band":"45-54"}', 'sig-seed-4', 'del-seed-4'),
    ('10000000-0000-0000-0000-000000000001', 'seed-q1-u5', 'No change. Same incentives, faster tooling.', '{"region":"SA","age_band":"25-34"}', 'sig-seed-5', 'del-seed-5'),
    ('10000000-0000-0000-0000-000000000001', 'seed-q1-u6', 'More honest — verified humans become the scarce signal.', '{"region":"NA","age_band":"25-34"}', 'sig-seed-6', 'del-seed-6'),
    ('10000000-0000-0000-0000-000000000001', 'seed-q1-u7', 'Hostile. Surveillance + automation never ends well.', '{"region":"AF","age_band":"18-24"}', 'sig-seed-7', 'del-seed-7')
  ON CONFLICT DO NOTHING RETURNING 1
)
INSERT INTO aggregates (question_id, total_answers, by_predicate) VALUES
  ('10000000-0000-0000-0000-000000000001', 142,
   '{"region:EU":48,"region:NA":42,"region:AS":31,"region:SA":12,"region:AF":9,"age_band:18-24":17,"age_band:25-34":61,"age_band:35-44":40,"age_band:45-54":24}')
ON CONFLICT (question_id) DO UPDATE SET total_answers = EXCLUDED.total_answers, by_predicate = EXCLUDED.by_predicate;

-- Q2: deep work hours
WITH env AS (
  INSERT INTO envelopes (question_id, unique_identifier, answer, disclosed_predicates, agent_signature, delegation_hash) VALUES
    ('10000000-0000-0000-0000-000000000002', 'seed-q2-u1', 'Two on good days, zero on most.', '{"region":"EU","occupation":"engineer"}', 'sig-q2-1', 'del-q2-1'),
    ('10000000-0000-0000-0000-000000000002', 'seed-q2-u2', '3-4 if I block calendar and disable notifications.', '{"region":"NA","occupation":"engineer"}', 'sig-q2-2', 'del-q2-2'),
    ('10000000-0000-0000-0000-000000000002', 'seed-q2-u3', 'Less than one. Meetings shred the morning.', '{"region":"NA","occupation":"manager"}', 'sig-q2-3', 'del-q2-3'),
    ('10000000-0000-0000-0000-000000000002', 'seed-q2-u4', '5+, but I work asynchronously.', '{"region":"EU","occupation":"writer"}', 'sig-q2-4', 'del-q2-4'),
    ('10000000-0000-0000-0000-000000000002', 'seed-q2-u5', 'Maybe 90 minutes total, in two sprints.', '{"region":"AS","occupation":"designer"}', 'sig-q2-5', 'del-q2-5')
  ON CONFLICT DO NOTHING RETURNING 1
)
INSERT INTO aggregates (question_id, total_answers, by_predicate) VALUES
  ('10000000-0000-0000-0000-000000000002', 97,
   '{"region:NA":34,"region:EU":33,"region:AS":18,"region:SA":7,"region:OC":5,"occupation:engineer":41,"occupation:manager":22,"occupation:writer":11,"occupation:designer":13,"occupation:other":10}')
ON CONFLICT (question_id) DO UPDATE SET total_answers = EXCLUDED.total_answers, by_predicate = EXCLUDED.by_predicate;

-- Q3: one good habit
WITH env AS (
  INSERT INTO envelopes (question_id, unique_identifier, answer, disclosed_predicates, agent_signature, delegation_hash) VALUES
    ('10000000-0000-0000-0000-000000000003', 'seed-q3-u1', 'Putting the phone in another room before bed.', '{"region":"EU","age_band":"25-34"}', 'sig-q3-1', 'del-q3-1'),
    ('10000000-0000-0000-0000-000000000003', 'seed-q3-u2', 'A morning walk with no audio at all.', '{"region":"NA","age_band":"35-44"}', 'sig-q3-2', 'del-q3-2'),
    ('10000000-0000-0000-0000-000000000003', 'seed-q3-u3', 'Strength training twice a week.', '{"region":"AS","age_band":"25-34"}', 'sig-q3-3', 'del-q3-3'),
    ('10000000-0000-0000-0000-000000000003', 'seed-q3-u4', 'Writing a single sentence in a journal each night.', '{"region":"OC","age_band":"45-54"}', 'sig-q3-4', 'del-q3-4')
  ON CONFLICT DO NOTHING RETURNING 1
)
INSERT INTO aggregates (question_id, total_answers, by_predicate) VALUES
  ('10000000-0000-0000-0000-000000000003', 88,
   '{"region:EU":29,"region:NA":26,"region:AS":18,"region:OC":8,"region:SA":7,"age_band:18-24":11,"age_band:25-34":36,"age_band:35-44":26,"age_band:45-54":15}')
ON CONFLICT (question_id) DO UPDATE SET total_answers = EXCLUDED.total_answers, by_predicate = EXCLUDED.by_predicate;

-- Q4: climate policy
INSERT INTO aggregates (question_id, total_answers, by_predicate) VALUES
  ('10000000-0000-0000-0000-000000000004', 213,
   '{"region:EU":78,"region:NA":54,"region:AS":41,"region:SA":18,"region:AF":15,"region:OC":7,"age_band:18-24":48,"age_band:25-34":80,"age_band:35-44":55,"age_band:45-54":30}')
ON CONFLICT (question_id) DO UPDATE SET total_answers = EXCLUDED.total_answers, by_predicate = EXCLUDED.by_predicate;
INSERT INTO envelopes (question_id, unique_identifier, answer, disclosed_predicates, agent_signature, delegation_hash) VALUES
  ('10000000-0000-0000-0000-000000000004', 'seed-q4-u1', 'A simple, global carbon price — refunded as a dividend.', '{"region":"EU","age_band":"25-34"}', 'sig-q4-1', 'del-q4-1'),
  ('10000000-0000-0000-0000-000000000004', 'seed-q4-u2', 'End fossil-fuel subsidies first; everything else follows.', '{"region":"NA","age_band":"35-44"}', 'sig-q4-2', 'del-q4-2'),
  ('10000000-0000-0000-0000-000000000004', 'seed-q4-u3', 'Massive direct funding for grid storage R&D.', '{"region":"AS","age_band":"25-34"}', 'sig-q4-3', 'del-q4-3')
ON CONFLICT DO NOTHING;

-- Q5: remote vs office
INSERT INTO aggregates (question_id, total_answers, by_predicate) VALUES
  ('10000000-0000-0000-0000-000000000005', 174,
   '{"region:NA":71,"region:EU":53,"region:AS":29,"region:SA":12,"region:OC":9,"occupation:engineer":68,"occupation:designer":21,"occupation:writer":18,"occupation:manager":34,"occupation:other":33}')
ON CONFLICT (question_id) DO UPDATE SET total_answers = EXCLUDED.total_answers, by_predicate = EXCLUDED.by_predicate;
INSERT INTO envelopes (question_id, unique_identifier, answer, disclosed_predicates, agent_signature, delegation_hash) VALUES
  ('10000000-0000-0000-0000-000000000005', 'seed-q5-u1', 'Better for execution, worse for serendipity.', '{"region":"NA","occupation":"engineer"}', 'sig-q5-1', 'del-q5-1'),
  ('10000000-0000-0000-0000-000000000005', 'seed-q5-u2', 'Just different. Both have a "mode tax".', '{"region":"EU","occupation":"manager"}', 'sig-q5-2', 'del-q5-2')
ON CONFLICT DO NOTHING;

-- Continent questions
INSERT INTO aggregates (question_id, total_answers, by_predicate) VALUES
  ('20000000-0000-0000-0000-000000000001', 64,
   '{"country:DE":18,"country:FR":11,"country:NL":8,"country:ES":7,"country:IT":6,"country:SE":5,"country:PL":4,"country:other":5,"age_band:25-34":28,"age_band:35-44":21,"age_band:45-54":15}'),
  ('20000000-0000-0000-0000-000000000002', 41,
   '{"country:DE":12,"country:FR":9,"country:IT":6,"country:CH":5,"country:AT":4,"country:NL":3,"country:other":2}'),
  ('20000000-0000-0000-0000-000000000003', 89,
   '{"country:US":58,"country:CA":21,"country:MX":10,"age_band:25-34":34,"age_band:35-44":30,"age_band:45-54":17,"age_band:18-24":8}'),
  ('20000000-0000-0000-0000-000000000004', 73,
   '{"country:US":47,"country:CA":18,"country:MX":8,"age_band:25-34":29,"age_band:35-44":24,"age_band:45-54":12,"age_band:18-24":8}'),
  ('20000000-0000-0000-0000-000000000005', 58,
   '{"country:CN":17,"country:IN":15,"country:JP":10,"country:KR":7,"country:SG":4,"country:ID":3,"country:VN":2}'),
  ('20000000-0000-0000-0000-000000000006', 47,
   '{"country:JP":13,"country:KR":9,"country:TW":7,"country:TH":6,"country:VN":5,"country:MY":4,"country:other":3}'),
  ('20000000-0000-0000-0000-000000000007', 35,
   '{"country:BR":15,"country:AR":7,"country:CO":6,"country:CL":4,"country:PE":3}'),
  ('20000000-0000-0000-0000-000000000008', 29,
   '{"country:NG":9,"country:ZA":7,"country:KE":5,"country:EG":4,"country:MA":2,"country:other":2}'),
  ('20000000-0000-0000-0000-000000000009', 18,
   '{"country:AU":11,"country:NZ":5,"country:FJ":2}')
ON CONFLICT (question_id) DO UPDATE SET total_answers = EXCLUDED.total_answers, by_predicate = EXCLUDED.by_predicate;

INSERT INTO envelopes (question_id, unique_identifier, answer, disclosed_predicates, agent_signature, delegation_hash) VALUES
  ('20000000-0000-0000-0000-000000000001', 'seed-c1-u1', 'Yes — open weights for any model used in admin decisions.', '{"country":"DE","age_band":"25-34"}', 'sig-c1-1', 'del-c1-1'),
  ('20000000-0000-0000-0000-000000000001', 'seed-c1-u2', 'Only above a usage threshold. Don''t kneecap startups.', '{"country":"FR","age_band":"35-44"}', 'sig-c1-2', 'del-c1-2'),
  ('20000000-0000-0000-0000-000000000001', 'seed-c1-u3', 'Yes, and require reproducible training datasets.', '{"country":"NL","age_band":"25-34"}', 'sig-c1-3', 'del-c1-3'),
  ('20000000-0000-0000-0000-000000000002', 'seed-c2-u1', 'High-speed rail yes; regional services no.', '{"country":"DE","age_band":"35-44"}', 'sig-c2-1', 'del-c2-1'),
  ('20000000-0000-0000-0000-000000000003', 'seed-c3-u1', 'Solvable. We just refuse to actually build.', '{"country":"US","age_band":"25-34"}', 'sig-c3-1', 'del-c3-1'),
  ('20000000-0000-0000-0000-000000000003', 'seed-c3-u2', 'Solvable in Toronto only by killing zoning.', '{"country":"CA","age_band":"35-44"}', 'sig-c3-2', 'del-c3-2'),
  ('20000000-0000-0000-0000-000000000004', 'seed-c4-u1', 'Yes — congestion, equity, climate. All three.', '{"country":"CA","age_band":"25-34"}', 'sig-c4-1', 'del-c4-1'),
  ('20000000-0000-0000-0000-000000000005', 'seed-c5-u1', 'Still accelerating in SEA, saturating in North Asia.', '{"country":"SG","age_band":"35-44"}', 'sig-c5-1', 'del-c5-1'),
  ('20000000-0000-0000-0000-000000000006', 'seed-c6-u1', 'Fukuoka. Cheaper, sunnier, calmer than Tokyo.', '{"country":"JP","age_band":"25-34"}', 'sig-c6-1', 'del-c6-1'),
  ('20000000-0000-0000-0000-000000000007', 'seed-c7-u1', 'Dominant by headcount, shrinking in revenue share.', '{"country":"BR","age_band":"35-44"}', 'sig-c7-1', 'del-c7-1'),
  ('20000000-0000-0000-0000-000000000008', 'seed-c8-u1', 'Renewable energy installation and operations.', '{"country":"NG","age_band":"25-34"}', 'sig-c8-1', 'del-c8-1'),
  ('20000000-0000-0000-0000-000000000009', 'seed-c9-u1', 'Yes — Pacific Islands can''t wait for global frameworks.', '{"country":"AU","age_band":"35-44"}', 'sig-c9-1', 'del-c9-1')
ON CONFLICT DO NOTHING;

-- Country questions
INSERT INTO aggregates (question_id, total_answers, by_predicate) VALUES
  ('30000000-0000-0000-0000-000000000001', 312,
   '{"region:northeast":81,"region:south":98,"region:midwest":63,"region:west":70,"age_band:18-24":61,"age_band:25-34":118,"age_band:35-44":74,"age_band:45-54":42,"age_band:55+":17}'),
  ('30000000-0000-0000-0000-000000000002', 184,
   '{"region:northeast":52,"region:south":48,"region:midwest":36,"region:west":48,"age_band:25-34":71,"age_band:35-44":52,"age_band:45-54":40,"age_band:55+":21}'),
  ('30000000-0000-0000-0000-000000000003', 96,
   '{"region:Berlin":21,"region:München":18,"region:Hamburg":14,"region:NRW":22,"region:other":21,"age_band:25-34":34,"age_band:35-44":29,"age_band:45-54":21,"age_band:18-24":12}'),
  ('30000000-0000-0000-0000-000000000004', 73,
   '{"region:Berlin":18,"region:München":14,"region:Hamburg":11,"region:other":30,"age_band:25-34":25,"age_band:35-44":24,"age_band:45-54":15,"age_band:18-24":9}'),
  ('30000000-0000-0000-0000-000000000005', 54,
   '{"region:Tokyo":24,"region:Osaka":11,"region:Kyushu":8,"region:other":11,"age_band:25-34":21,"age_band:35-44":18,"age_band:45-54":11,"age_band:18-24":4}'),
  ('30000000-0000-0000-0000-000000000006', 39,
   '{"region:Tokyo":15,"region:Osaka":9,"region:other":15,"age_band:25-34":16,"age_band:35-44":14,"age_band:45-54":7,"age_band:18-24":2}'),
  ('30000000-0000-0000-0000-000000000007', 121,
   '{"region:Sudeste":52,"region:Sul":24,"region:Nordeste":28,"region:Norte":7,"region:CentroOeste":10}'),
  ('30000000-0000-0000-0000-000000000008', 168,
   '{"region:North":42,"region:South":48,"region:West":41,"region:East":37,"age_band:18-24":58,"age_band:25-34":74,"age_band:35-44":26,"age_band:45-54":10}'),
  ('30000000-0000-0000-0000-000000000009', 92,
   '{"region:England":61,"region:Scotland":15,"region:Wales":9,"region:NI":7,"age_band:25-34":31,"age_band:35-44":28,"age_band:45-54":19,"age_band:55+":14}'),
  ('30000000-0000-0000-0000-00000000000a', 47,
   '{"region:NSW":17,"region:VIC":14,"region:QLD":8,"region:WA":5,"region:other":3}'),
  ('30000000-0000-0000-0000-00000000000b', 56,
   '{"region:Lagos":24,"region:Abuja":11,"region:South":12,"region:North":9}'),
  ('30000000-0000-0000-0000-00000000000c', 62,
   '{"region:IDF":19,"region:Sud":13,"region:Ouest":11,"region:Est":9,"region:Nord":10}')
ON CONFLICT (question_id) DO UPDATE SET total_answers = EXCLUDED.total_answers, by_predicate = EXCLUDED.by_predicate;

INSERT INTO envelopes (question_id, unique_identifier, answer, disclosed_predicates, agent_signature, delegation_hash) VALUES
  ('30000000-0000-0000-0000-000000000001', 'seed-us1-u1', 'Yes, indexed to median rent — $15 already lags.', '{"region":"northeast","age_band":"25-34"}', 'sig-us1-1', 'del-us1-1'),
  ('30000000-0000-0000-0000-000000000001', 'seed-us1-u2', 'Raise it, but only with regional bands.', '{"region":"south","age_band":"35-44"}', 'sig-us1-2', 'del-us1-2'),
  ('30000000-0000-0000-0000-000000000001', 'seed-us1-u3', 'No — small businesses outside coastal cities can''t carry it.', '{"region":"midwest","age_band":"45-54"}', 'sig-us1-3', 'del-us1-3'),
  ('30000000-0000-0000-0000-000000000001', 'seed-us1-u4', 'Yes, with a phase-in for small employers.', '{"region":"west","age_band":"25-34"}', 'sig-us1-4', 'del-us1-4'),
  ('30000000-0000-0000-0000-000000000002', 'seed-us2-u1', 'Yes — capture economic rent, free the productive sector.', '{"region":"northeast","age_band":"25-34"}', 'sig-us2-1', 'del-us2-1'),
  ('30000000-0000-0000-0000-000000000002', 'seed-us2-u2', 'In theory yes; the politics make it impossible.', '{"region":"west","age_band":"35-44"}', 'sig-us2-2', 'del-us2-2'),
  ('30000000-0000-0000-0000-000000000003', 'seed-de1-u1', 'Ja, aber finanziert über eine bundesweite Pendlerumlage.', '{"region":"Berlin","age_band":"25-34"}', 'sig-de1-1', 'del-de1-1'),
  ('30000000-0000-0000-0000-000000000003', 'seed-de1-u2', 'Nein. Die Länder müssen es nachhaltig finanzieren.', '{"region":"München","age_band":"35-44"}', 'sig-de1-2', 'del-de1-2'),
  ('30000000-0000-0000-0000-000000000004', 'seed-de2-u1', 'Weniger Bauvorschriften. Mietpreisbremsen helfen kurzfristig.', '{"region":"Berlin","age_band":"25-34"}', 'sig-de2-1', 'del-de2-1'),
  ('30000000-0000-0000-0000-000000000005', 'seed-jp1-u1', 'Yes — Tokyo startups hire in English now without controversy.', '{"region":"Tokyo","age_band":"25-34"}', 'sig-jp1-1', 'del-jp1-1'),
  ('30000000-0000-0000-0000-000000000006', 'seed-jp2-u1', 'Slowly. Trial companies report 30% productivity wins.', '{"region":"Tokyo","age_band":"35-44"}', 'sig-jp2-1', 'del-jp2-1'),
  ('30000000-0000-0000-0000-000000000007', 'seed-br1-u1', 'Sim — quase não uso dinheiro vivo desde 2022.', '{"region":"Sudeste","age_band":"25-34"}', 'sig-br1-1', 'del-br1-1'),
  ('30000000-0000-0000-0000-000000000007', 'seed-br1-u2', 'Mudou tudo no comércio pequeno.', '{"region":"Nordeste","age_band":"35-44"}', 'sig-br1-2', 'del-br1-2'),
  ('30000000-0000-0000-0000-000000000008', 'seed-in1-u1', 'Yes — rural adoption still has miles to go.', '{"region":"South","age_band":"25-34"}', 'sig-in1-1', 'del-in1-1'),
  ('30000000-0000-0000-0000-000000000008', 'seed-in1-u2', 'Maybe — merchant fees may finally land.', '{"region":"North","age_band":"35-44"}', 'sig-in1-2', 'del-in1-2'),
  ('30000000-0000-0000-0000-000000000009', 'seed-gb1-u1', 'Reformable, but the workforce model is what needs rethinking.', '{"region":"England","age_band":"35-44"}', 'sig-gb1-1', 'del-gb1-1'),
  ('30000000-0000-0000-0000-00000000000a', 'seed-au1-u1', 'Yes — negative gearing is a fairness problem.', '{"region":"NSW","age_band":"25-34"}', 'sig-au1-1', 'del-au1-1'),
  ('30000000-0000-0000-0000-00000000000b', 'seed-ng1-u1', 'Painful now, but the parallel market is shrinking.', '{"region":"Lagos","age_band":"25-34"}', 'sig-ng1-1', 'del-ng1-1'),
  ('30000000-0000-0000-0000-00000000000c', 'seed-fr1-u1', 'Viable dans certains services; pas partout.', '{"region":"IDF","age_band":"35-44"}', 'sig-fr1-1', 'del-fr1-1')
ON CONFLICT DO NOTHING;

COMMIT;
