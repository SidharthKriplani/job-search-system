-- ============================================================================
-- COMPANIES DICTIONARY + CUMULATIVE FACETS ("Companies v1")
-- Idempotent, non-destructive. Run whole file in the Supabase SQL editor.
--
--  companies    — canonical employer directory: careers_url (the fallback link
--                 when a company has no open matching roles), ats_platform,
--                 last_open_role_at. Seeded from the ATS detector; the nightly
--                 refresh keeps last_open_role_at current from jobs_pool.
--  facet_terms  — cumulative facet dictionary (company/location/position).
--                 Terms only ever get ADDED; the feed's filter options no
--                 longer shrink when jobs close. refresh_facet_terms() is
--                 self-throttled (12h) so callers can fire it blindly.
-- ============================================================================

CREATE TABLE IF NOT EXISTS companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_name  TEXT NOT NULL UNIQUE,
    careers_url     TEXT,
    ats_platform    TEXT,
    aliases         JSONB DEFAULT '[]',
    first_seen_at   TIMESTAMPTZ DEFAULT NOW(),
    last_open_role_at TIMESTAMPTZ
);
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "companies readable" ON companies;
CREATE POLICY "companies readable" ON companies FOR SELECT TO authenticated USING (true);

CREATE TABLE IF NOT EXISTS facet_terms (
    kind          TEXT NOT NULL,             -- 'company' | 'location' | 'position'
    value         TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (kind, value)
);
ALTER TABLE facet_terms ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "facet_terms readable" ON facet_terms;
CREATE POLICY "facet_terms readable" ON facet_terms FOR SELECT TO authenticated USING (true);

-- refresh bookkeeping (single row)
CREATE TABLE IF NOT EXISTS facet_terms_meta (
    id            INT PRIMARY KEY DEFAULT 1,
    refreshed_at  TIMESTAMPTZ DEFAULT 'epoch'
);
INSERT INTO facet_terms_meta (id) VALUES (1) ON CONFLICT DO NOTHING;
ALTER TABLE facet_terms_meta ENABLE ROW LEVEL SECURITY;

-- Self-throttled refresh: upserts distinct terms from jobs_pool (global,
-- already deduped) + stamps companies.last_open_role_at. Cheap no-op when
-- called within 12h of the last refresh. SECURITY DEFINER so the
-- authenticated client may trigger it without table write grants.
CREATE OR REPLACE FUNCTION refresh_facet_terms()
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  IF (SELECT refreshed_at FROM facet_terms_meta WHERE id = 1) > NOW() - INTERVAL '12 hours' THEN
    RETURN;
  END IF;
  UPDATE facet_terms_meta SET refreshed_at = NOW() WHERE id = 1;

  INSERT INTO facet_terms (kind, value)
  SELECT 'company', company FROM jobs_pool
  WHERE company IS NOT NULL AND company <> '' GROUP BY company
  ON CONFLICT (kind, value) DO UPDATE SET last_seen_at = NOW();

  INSERT INTO facet_terms (kind, value)
  SELECT 'location', location_city FROM jobs_pool
  WHERE location_city IS NOT NULL AND location_city <> '' GROUP BY location_city
  ON CONFLICT (kind, value) DO UPDATE SET last_seen_at = NOW();

  INSERT INTO facet_terms (kind, value)
  SELECT 'position', position FROM jobs_pool
  WHERE position IS NOT NULL AND position <> '' GROUP BY position
  ON CONFLICT (kind, value) DO UPDATE SET last_seen_at = NOW();

  -- companies directory: register unseen employers + stamp freshness
  INSERT INTO companies (canonical_name, last_open_role_at)
  SELECT company, MAX(last_seen_at) FROM jobs_pool
  WHERE company IS NOT NULL AND company <> '' GROUP BY company
  ON CONFLICT (canonical_name) DO UPDATE
    SET last_open_role_at = EXCLUDED.last_open_role_at;
END $$;

GRANT EXECUTE ON FUNCTION refresh_facet_terms() TO authenticated;

-- Seed from scripts/detect_ats.py output (205 companies, generated 2026-07-16)
INSERT INTO companies (canonical_name, careers_url, ats_platform) VALUES
  ('AMD India', 'https://careers.amd.com/careers-home/jobs', 'icims'),
  ('Accenture India', 'https://www.accenture.com/us-en/careers', 'workday'),
  ('Acko', 'https://www.acko.com/careers/', 'custom/unknown'),
  ('Acuity Knowledge Partners', 'https://www.acuityanalytics.com/working-here/', 'darwinbox'),
  ('Adobe India', 'https://careers.adobe.com/us/en', 'phenom'),
  ('Airbus India', 'https://www.airbus.com/en/careers', 'workday'),
  ('Airtel', 'https://www.airtel.in/b2b/global-connectivity-solutions', 'custom/unknown'),
  ('Amazon India', 'https://jobs.amazon.in/', 'custom/unknown'),
  ('American Express India', 'https://careers.americanexpress.com/en/sites/CX_1', 'oracle_orc'),
  ('Analog Devices India', 'https://www.google.com/search?q=%22Analog+Devices+India%22+careers', 'custom/unknown'),
  ('Angel One', 'https://www.angelone.in/careers', 'custom/unknown'),
  ('Apna', 'https://careers.apna.co/', 'workable'),
  ('Apple India', 'https://www.apple.com/careers/us/', 'custom/unknown'),
  ('Arm India', 'https://careers.arm.com/', 'icims'),
  ('Asian Paints', 'https://careers.asianpaints.com/', 'successfactors'),
  ('Ather Energy', 'https://careers.atherenergy.com/', 'custom/unknown'),
  ('Atlassian', 'https://www.atlassian.com/company/careers', 'custom/unknown'),
  ('Axis Bank', 'https://www.axis.bank.in/careers', 'custom/unknown'),
  ('BSE', 'https://www.bseindia.com/careers', 'custom/unknown'),
  ('BYJU''S', 'https://byjus.com/careers-at-byjus/', 'custom/unknown'),
  ('Bajaj Finance', 'https://www.bajajfinserv.in/', 'custom/unknown'),
  ('Bajaj Finserv', 'https://www.bajajfinserv.in/', 'custom/unknown'),
  ('BharatPe', 'https://bharatpe.com/careers', 'custom/unknown'),
  ('BigBasket', 'https://careers.bigbasket.com/', 'darwinbox'),
  ('Birlasoft', 'https://jobs.birlasoft.com/', 'successfactors'),
  ('Blinkit', 'https://www.google.com/search?q=%22Blinkit%22+careers', 'custom/unknown'),
  ('Boeing India', 'https://jobs.boeing.com', 'workday'),
  ('Bosch Group', 'https://www.bosch.in/careers/', 'custom/unknown'),
  ('Bridgei2i', 'https://www.accenture.com/us-en/careers/explore-careers/area-of-interest/ai-data-science-careers', 'workday'),
  ('Britannia', 'https://www.britannia.co.in/careers', 'zoho_workerly/custom'),
  ('BrowserStack', 'https://www.browserstack.com:443/careers', 'workday'),
  ('CAMS', 'https://www.camsonline.com/careers', 'custom/unknown'),
  ('CRED', 'https://careers.cred.club/', 'custom/unknown'),
  ('CRISIL', 'https://www.google.com/search?q=%22CRISIL%22+careers', 'custom/unknown'),
  ('Capgemini India', 'https://careers.capgemini.com/', 'successfactors'),
  ('CarDekho', 'https://careers.cardekho.com/', 'darwinbox'),
  ('Cars24', 'https://careers.cars24.com/', 'custom/unknown'),
  ('Cashfree Payments', 'https://www.cashfree.com:443/careers', 'custom/unknown'),
  ('Chargebee', 'https://jobs.chargebee.com:443/', 'successfactors'),
  ('Cisco India', 'https://careers.cisco.com/global/en', 'phenom'),
  ('Cleartrip', 'https://careers.cleartrip.com/', 'zoho_workerly/custom'),
  ('CleverTap', 'https://clevertap.com/careers/', 'kula'),
  ('Coforge', 'https://careers.coforge.com/coforge/', 'custom/unknown'),
  ('Cognizant', 'https://www.google.com/search?q=%22Cognizant%22+careers', 'custom/unknown'),
  ('Cyient', 'https://careers.cyient.com/cyient/', 'custom/unknown'),
  ('Dabur', 'https://www.google.com/search?q=%22Dabur%22+careers', 'custom/unknown'),
  ('Darwinbox', 'https://darwinbox.com/en-us', 'darwinbox'),
  ('Delhivery', 'https://www.delhivery.com:443/careers', 'custom/unknown'),
  ('Dell India', 'https://www.google.com/search?q=%22Dell+India%22+careers', 'custom/unknown'),
  ('Digit Insurance', 'https://www.godigit.com/careers', 'darwinbox'),
  ('Dream11', 'https://www.dream11.com/', 'custom/unknown'),
  ('EXL Service', 'https://www.exlservice.com/careers', 'oracle_orc'),
  ('Ecom Express', 'https://www.google.com/search?q=%22Ecom+Express%22+careers', 'custom/unknown'),
  ('Edelweiss', 'https://www.google.com/search?q=%22Edelweiss%22+careers', 'custom/unknown'),
  ('Evalueserve', 'https://www.evalueserve.com/careers/', 'custom/unknown'),
  ('Exotel', 'https://exotel.com/about-us/careers/', 'custom/unknown'),
  ('Flipkart', 'https://www.google.com/search?q=%22Flipkart%22+careers', 'custom/unknown'),
  ('Fractal Analytics', 'https://fractal.wd1.myworkdayjobs.com/Careers', 'workday'),
  ('Freshworks', 'https://careers.smartrecruiters.com/Freshworks', 'smartrecruiters'),
  ('GE HealthCare India', 'https://www.google.com/search?q=%22GE+HealthCare+India%22+careers', 'custom/unknown'),
  ('Games24x7', 'https://www.google.com/search?q=%22Games24x7%22+careers', 'custom/unknown'),
  ('Genpact', 'https://www.genpact.com/careers', 'workday'),
  ('Glance', 'https://glance.com/us/careers', 'greenhouse'),
  ('Goldman Sachs India', 'https://www.goldmansachs.com/careers', 'custom/unknown'),
  ('Google India', 'https://www.google.com/about/careers/applications/', 'custom/unknown'),
  ('Gramener', 'https://gramener.com/careers/', 'custom/unknown'),
  ('Groww', 'https://groww.in/careers', 'greenhouse'),
  ('Gupshup', 'https://www.gupshup.ai:443/careers', 'custom/unknown'),
  ('HCLTech', 'https://careers.hcltech.com/', 'successfactors'),
  ('HDFC Bank', 'https://www.google.com/search?q=%22HDFC+Bank%22+careers', 'custom/unknown'),
  ('HDFC Life', 'https://www.google.com/search?q=%22HDFC+Life%22+careers', 'custom/unknown'),
  ('HSBC India', 'https://www.hsbc.com/careers', 'custom/unknown'),
  ('Haptik', 'https://www.haptik.ai/careers', 'freshteam'),
  ('Hasura', 'https://promptql.io/careers', 'custom/unknown'),
  ('HealthifyMe', 'https://www.healthifyme.com:443/careers/', 'darwinbox'),
  ('Hindustan Unilever', 'https://www.google.com/search?q=%22Hindustan+Unilever%22+careers', 'custom/unknown'),
  ('Housing.com', 'https://careers.housing.com/', 'custom/unknown'),
  ('IBM India', 'https://careers.ibm.com/en_US/careers', 'custom/unknown'),
  ('ICICI Bank', 'https://www.google.com/search?q=%22ICICI+Bank%22+careers', 'custom/unknown'),
  ('ICICI Lombard', 'https://www.google.com/search?q=%22ICICI+Lombard%22+careers', 'custom/unknown'),
  ('ICRA', 'https://www.icra.in/Home/SessionTimeOut', 'custom/unknown'),
  ('IDFC FIRST Bank', 'https://www.google.com/search?q=%22IDFC+FIRST+Bank%22+careers', 'custom/unknown'),
  ('IIFL', 'https://www.iifl.com/finance/career', 'darwinbox'),
  ('ITC', 'https://itcportal.com/careers.html', 'custom/unknown'),
  ('InMobi', 'https://www.inmobi.com/company/careers', 'custom/unknown'),
  ('Infosys', 'https://www.google.com/search?q=%22Infosys%22+careers', 'custom/unknown'),
  ('Intuit India', 'https://www.intuit.com/careers/', 'custom/unknown'),
  ('JP Morgan India', 'https://www.jpmorganchase.com/careers?redirect=careers_jpm', 'oracle_orc'),
  ('Jio Platforms', 'https://careers.jio.com/', 'custom/unknown'),
  ('Jupiter', 'https://jupiter.money/careers/', 'keka'),
  ('Juspay', 'https://juspay.io/careers', 'custom/unknown'),
  ('KFintech', 'https://www.kfintech.com/jobs/', 'custom/unknown'),
  ('KPIT', 'https://www.kpit.com/careers-overview/', 'custom/unknown'),
  ('Kotak Mahindra Bank', 'https://www.kotak.com/error/err.html', 'custom/unknown'),
  ('KreditBee', 'https://www.kreditbee.in/careers', 'custom/unknown'),
  ('Krutrim', 'https://www.olakrutrim.com/', 'custom/unknown'),
  ('L&T', 'https://careers.larsentoubro.com/', 'custom/unknown'),
  ('LTTS', 'https://jobs.ltts.com/', 'successfactors'),
  ('LTIMindtree', 'https://careers.ltimindtree.com/', 'successfactors'),
  ('LatentView', 'https://www.google.com/search?q=%22LatentView%22+careers', 'custom/unknown'),
  ('Lenskart', 'https://ainterviews.com/job_board/lenskart_ho/', 'custom/unknown'),
  ('Lowe''s India', 'https://talent.lowes.com/us/en', 'phenom'),
  ('MPL', 'https://www.google.com/search?q=%22MPL%22+careers', 'custom/unknown'),
  ('Mahindra', 'https://www.mahindra.com/career', 'custom/unknown'),
  ('MakeMyTrip', 'https://careers.makemytrip.com/', 'custom/unknown'),
  ('Mamaearth', 'https://www.google.com/search?q=%22Mamaearth%22+careers', 'custom/unknown'),
  ('Marico', 'https://marico.com/global/careers', 'custom/unknown'),
  ('Maruti Suzuki', 'https://www.google.com/search?q=%22Maruti+Suzuki%22+careers', 'custom/unknown'),
  ('Meesho', 'https://jobs.meesho.com/', 'custom/unknown'),
  ('Meta India', 'https://www.metacareers.com/?utm_source=meta.com&utm_medium=redirect', 'custom/unknown'),
  ('Micron India', 'https://careers.micron.com/careers', 'workday'),
  ('Microsoft India', 'https://careers.microsoft.com/v2/global/en/home.html', 'custom/unknown'),
  ('MoEngage', 'https://www.moengage.com/careers/', 'custom/unknown'),
  ('Morgan Stanley India', 'https://www.morganstanley.com/people', 'custom/unknown'),
  ('Motilal Oswal', 'https://www.motilaloswal.com/careers', 'custom/unknown'),
  ('Mphasis', 'https://careers.mphasis.com/home.html', 'custom/unknown'),
  ('Mu Sigma', 'https://www.mu-sigma.com/career/', 'custom/unknown'),
  ('Myntra', 'https://careers.myntra.com/', 'custom/unknown'),
  ('NSE', 'https://www.google.com/search?q=%22NSE%22+careers', 'custom/unknown'),
  ('Navi', 'https://navi.com/careers', 'zoho_workerly/custom'),
  ('Nestle India', 'https://www.google.com/search?q=%22Nestle+India%22+careers', 'custom/unknown'),
  ('Netcore Cloud', 'https://netcorecloud.com/careers', 'custom/unknown'),
  ('Netflix India', 'https://www.netflix.com/NotFound?prev=https%3A%2F%2Fwww.netflix.com%2Fcareers', 'custom/unknown'),
  ('NoBroker', 'https://www.nobroker.in/careers', 'custom/unknown'),
  ('Nutanix India', 'https://jobs.jobvite.com/nutanix', 'jobvite'),
  ('Nykaa', 'https://careers.nykaa.com/', 'custom/unknown'),
  ('OYO', 'https://www.oyorooms.com/', 'custom/unknown'),
  ('Observe.AI', 'https://observe.ai/careers', 'greenhouse'),
  ('Ola', 'https://www.olacabs.com/careers', 'zoho_workerly/custom'),
  ('Ola Electric', 'https://www.olaelectric.com/careers', 'zoho_workerly/custom'),
  ('Oracle India', 'https://careers.oracle.com/en/sites/jobsearch', 'oracle_orc'),
  ('Ozonetel', 'https://ozonetel.com/careers/', 'custom/unknown'),
  ('Palo Alto Networks India', 'https://jobs.paloaltonetworks.com/en', 'custom/unknown'),
  ('PayPal India', 'https://www.google.com/search?q=%22PayPal+India%22+careers', 'custom/unknown'),
  ('Paytm', 'https://paytm.com/careers', 'lever'),
  ('Persistent Systems', 'https://careers.persistent.com/', 'custom/unknown'),
  ('PharmEasy', 'https://pharmeasy.in/careers/', 'darwinbox'),
  ('PhonePe', 'https://www.phonepe.com/careers/', 'custom/unknown'),
  ('PhysicsWallah', 'https://www.google.com/search?q=%22PhysicsWallah%22+careers', 'custom/unknown'),
  ('Pine Labs', 'https://www.pinelabs.com/careers', 'custom/unknown'),
  ('Plum', 'https://www.plumhq.com/careers', 'kula'),
  ('PolicyBazaar', 'https://www.policybazaar.com/careers/', 'custom/unknown'),
  ('Postman', 'https://www.postman.com/company/careers/', 'custom/unknown'),
  ('Practo', 'https://careers.practo.com/practo/', 'custom/unknown'),
  ('Pure Storage India', 'https://www.everpuredata.com/company/careers.html', 'custom/unknown'),
  ('Qualcomm India', 'https://careers.qualcomm.com/careers', 'eightfold'),
  ('Quantiphi', 'https://quantiphi.com/careers/', 'workday'),
  ('RBL Bank', 'https://www.rbl.bank.in:443/careers', 'custom/unknown'),
  ('Rapido', 'https://www.google.com/search?q=%22Rapido%22+careers', 'custom/unknown'),
  ('Razorpay', 'https://razorpay.com/careers/', 'greenhouse'),
  ('Red Hat India', 'https://www.redhat.com/en/jobs', 'custom/unknown'),
  ('Reliance Jio', 'https://careers.jio.com/', 'custom/unknown'),
  ('Reliance Retail', 'https://www.google.com/search?q=%22Reliance+Retail%22+careers', 'custom/unknown'),
  ('SAP Labs India', 'https://jobs.sap.com/', 'successfactors'),
  ('SBI', 'https://sbi.bank.in/web/careers', 'custom/unknown'),
  ('SG Analytics', 'https://www.sganalytics.com:443/', 'custom/unknown'),
  ('Salesforce India', 'https://www.salesforce.com/company/careers/?bc=OTH', 'custom/unknown'),
  ('Sarvam AI', 'https://www.sarvam.ai/careers', 'ashby'),
  ('ServiceNow India', 'https://www.google.com/search?q=%22ServiceNow+India%22+careers', 'custom/unknown'),
  ('ShareChat', 'https://sharechat.com/careers', 'custom/unknown'),
  ('Shell India', 'https://shell.wd3.myworkdayjobs.com/shellcareers', 'workday'),
  ('Siemens India', 'https://www.siemens.com/en-us/company/jobs/', 'custom/unknown'),
  ('Sigmoid', 'https://www.sigmoid.com/careers/', 'custom/unknown'),
  ('Spinny', 'https://www.spinny.com/careers/', 'custom/unknown'),
  ('Standard Chartered GBS', 'https://www.sc.com/en/global-careers/', 'custom/unknown'),
  ('Swiggy', 'https://careers.swiggy.com/', 'custom/unknown'),
  ('TCS', 'https://www.google.com/search?q=%22TCS%22+careers', 'custom/unknown'),
  ('Target India', 'https://corporate.target.com/careers', 'workday'),
  ('Tata 1mg', 'https://www.1mg.com/jobs', 'darwinbox'),
  ('Tata Digital', 'https://www.tataneu.com/careers', 'custom/unknown'),
  ('Tata Elxsi', 'https://www.tataelxsi.com/careers', 'custom/unknown'),
  ('Tata Motors', 'https://careers.tatamotors.com/', 'successfactors'),
  ('Tech Mahindra', 'https://careers.techmahindra.com/', 'custom/unknown'),
  ('Tesco Bengaluru', 'https://careers.tesco.com/en_GB/careers', 'avature'),
  ('Texas Instruments India', 'https://careers.ti.com/en/sites/CX', 'oracle_orc'),
  ('Tiger Analytics', 'https://www.tigeranalytics.com/about-us/current-openings/', 'workable'),
  ('Tredence', 'https://www.google.com/search?q=%22Tredence%22+careers', 'custom/unknown'),
  ('UBS India', 'https://careers.ubs.com/', 'custom/unknown'),
  ('Uber', 'https://www.google.com/search?q=%22Uber%22+careers', 'custom/unknown'),
  ('Uber India', 'https://www.google.com/search?q=%22Uber+India%22+careers', 'custom/unknown'),
  ('Unacademy', 'https://unacademy.com/careers', 'darwinbox'),
  ('Upstox', 'https://upstox.com/careers/', 'custom/unknown'),
  ('Urban Company', 'https://careers.urbancompany.com/', 'custom/unknown'),
  ('VMware India', 'https://www.broadcom.com/company/careers', 'custom/unknown'),
  ('Vedantu', 'https://courses.vedantu.com/career-page/', 'custom/unknown'),
  ('Visa India', 'https://corporate.visa.com/en/careers.html', 'workday'),
  ('WNS', 'https://www.wns.com/about-us/careers', 'custom/unknown'),
  ('Walmart Global Tech India', 'https://careers.walmart.com/us/en/home', 'custom/unknown'),
  ('WebEngage', 'https://webengage.com/current-openings/', 'custom/unknown'),
  ('Whatfix', 'https://whatfix.com/careers', 'custom/unknown'),
  ('Wipro', 'https://careers.wipro.com/', 'successfactors'),
  ('Yellow.ai', 'https://careers.yellow.ai/jobs/Careers', 'custom/unknown'),
  ('Yes Bank', 'https://www.google.com/search?q=%22Yes+Bank%22+careers', 'custom/unknown'),
  ('Zensar', 'https://www.zensar.com/careers', 'oracle_orc'),
  ('Zepto', 'https://zepto.talentrecruit.com/career-page', 'custom/unknown'),
  ('Zerodha', 'https://careers.zerodha.com/', 'custom/unknown'),
  ('Zoho', 'https://www.zoho.com/careers/', 'custom/unknown'),
  ('Zomato', 'https://www.eternal.com/careers/', 'custom/unknown'),
  ('Zscaler India', 'https://www.zscaler.com:443/careers', 'custom/unknown'),
  ('boAt', 'https://www.google.com/search?q=%22boAt%22+careers', 'custom/unknown'),
  ('bp India (Castrol/TSI)', 'https://careers.bp.com/', 'workday'),
  ('cult.fit', 'https://careers.cult.fit/cult/', 'custom/unknown'),
  ('ixigo', 'https://www.google.com/search?q=%22ixigo%22+careers', 'custom/unknown'),
  ('slice', 'https://slice.bank.in/careers/', 'custom/unknown'),
  ('upGrad', 'https://careers.upgrad.com/', 'custom/unknown')
ON CONFLICT (canonical_name) DO UPDATE
  SET careers_url = EXCLUDED.careers_url, ats_platform = EXCLUDED.ats_platform;

-- Prime everything once at install time (bypasses the 12h throttle by
-- resetting the meta stamp first).
UPDATE facet_terms_meta SET refreshed_at = 'epoch' WHERE id = 1;
SELECT refresh_facet_terms();

-- Sanity:
--   SELECT count(*) FROM companies;
--   SELECT kind, count(*) FROM facet_terms GROUP BY kind;
