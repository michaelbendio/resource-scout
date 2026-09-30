"""Authored preparation decisions for the bounded Housing trial; no network/imports."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = []
def add(key, name, where, phone, website, kinds, groups, services, eligibility, population, connect, limitation, reason, sources, seed, duplicate="Distinct agency and direct program intake.", email="", hours=""):
    rows.append(dict(key=key, name=name, where=where, phone=phone, website=website,
        kinds=kinds, groups=groups, sections=[services, eligibility, population, connect, limitation],
        reason=reason, sources=sources, seed=seed, duplicateDecision=duplicate,
        email=email, hours=hours))

add('housing-connect','Housing Connect — affordable housing applications','Salt Lake County; phone and online intake','801-284-4400','https://housingconnect.org/',[1],['seniors','disabilities'],
    'Subsidized rental housing and applications for Housing Connect properties.',
    'Income and household rules depend on the property or voucher program; some properties target older adults or people with disabilities.',
    'Salt Lake County households needing affordable housing.',
    'Call or follow Apply Online on the official website to check current waiting lists.',
    'Waiting-list admission is not an offer of housing. Published announcements do not establish current availability; confirm each waiting list directly.',
    'Provides the county housing-authority route, covering subsidized rentals without listing every property separately.',
    ['https://housingconnect.org/','https://www.affordablehousing.com/housing-authority-ut/housing-connect-348/'],'county-list',email='info@housingconnect.org')

add('haslc','Housing Authority of Salt Lake City — housing applications','Salt Lake City / Salt Lake valley; phone and online intake','801-487-2161','https://haslcutah.org/apply-for-housing/',[1],[],
    'Applications for public, subsidized and affordable rental housing.',
    'Each property or program sets income and household requirements; use the options open to direct applicants.',
    'Low-income households seeking housing in the Salt Lake valley.',
    'Call the authority or use its Apply for Housing page to identify an eligible waiting list.',
    'Some lists are closed, and waits can last years. This is not emergency placement; some specialized programs require referrals.',
    'Adds a separate authority and property portfolio alongside Housing Connect; compare eligible lists rather than submitting duplicate applications.',
    ['https://haslcutah.org/','https://haslcutah.org/apply-for-housing/'],'city-guide',email='contact@haslcutah.org')

add('uca-rent','Utah Community Action — rent and deposit help','Salt Lake County; start online or by phone','801-359-2444','https://utahca.org/case-management-housing/',[2],[],
    'Help with rent or a rental deposit after a financial crisis.',
    'An unexpected financial crisis and an existing or obtainable lease; staff determine funding eligibility.',
    'Households in the local service area facing housing instability.',
    'Apply online; call intake for questions. Phone hours: weekdays 9–5.',
    'Payments go to landlords. Mortgage, family and roommate payments are excluded. Appointments may take weeks; assistance is not guaranteed.',
    'Covers emergency rent and deposit help through a direct local application.',
    ['https://utahca.org/case-management-housing/','https://www.slc.gov/access-belonging/wp-content/uploads/sites/57/2026/01/2025-07_CommunityResourceGuide-WebReady_01-26-1.pdf'],'city-guide',
    duplicate='Separate from UCA mediation: financial screening and rental-assistance intake use 801-359-2444.',email='housingintake@utahca.org',hours='Monday–Friday 9 am–5 pm')

add('tenant-center','Salt Lake City Tenant Resource Center','501 East 1700 South, Salt Lake City, UT','801-893-3779','https://www.slc.gov/can/renters/',[10,2],[],
    'One-to-one rental housing navigation and screening for relocation assistance.',
    'Salt Lake City renters. RAFT assistance concerns displacement from repairs, demolition or changes to income restrictions.',
    'City tenants who need help understanding housing options or a qualifying forced move.',
    'Call CDCU or use Get Help with Housing on the city page. In-person hours: Monday–Thursday 9–5; Friday 9–noon.',
    'RAFT is not general rent assistance. The navigator cannot guarantee funding, a rental or legal representation.',
    'Adds a human navigator for renters whose situation does not fit a single application; RAFT covers a specific displacement problem.',
    ['https://www.slc.gov/can/renters/'],'city-guide',
    duplicate='CDCU also has a homebuyer record: this city-funded renter service has different eligibility and phone (801-893-3779 versus 801-994-7222).',hours='Monday–Thursday 9 am–5 pm; Friday 9 am–noon')

add('milestone','Salt Lake County Milestone Transitional Living','Salt Lake County; contact program before visiting','801-518-0292','https://www.saltlakecounty.gov/youth/youth-programs/transitional-living/',[3],['young-adults'],
    'Transitional housing with employment and independent-living support.',
    'Young adults ages 18–21 at risk of homelessness or without housing; participants must follow program rules and pay program fees.',
    'Young adults preparing to live independently.',
    'Contact the program manager directly or follow the county page’s Milestone Referral Application link; ask about screening and openings.',
    'Fees start at $200 monthly and increase over time. Substance-free living, random drug testing and no pets are stated conditions. No immediate vacancy is promised.',
    'Adds an age-specific transitional route for young adults who cannot use the single-parent starter.',
    ['https://www.saltlakecounty.gov/youth/youth-programs/transitional-living/','https://www.saltlakecounty.gov/globalassets/1-site-files/youth-services/youth-programs/milestone-transitional-living-program/milestone-overview-2026.pdf'],'checklist-gap')

add('lifestart','Family Support Center — LifeStart Village','Salt Lake County; administrative contact in Taylorsville','801-955-9110','https://familysupportcenter.org/services/lifestart-village',[3],['single-parents'],
    'Apartments with case management and practical support toward independent housing.',
    'Single-parent families; contact LifeStart for the full admissions requirements and current availability.',
    'Single parents and their children rebuilding housing stability.',
    'Call the Family Support Center’s main number and ask for LifeStart admissions, or use its program page.',
    'The program describes stays of up to five years. It is not an emergency shelter; rent, screening, waiting time and the visit address need confirmation.',
    'Covers a sustained housing program for single-parent families, rather than another overnight shelter.',
    ['https://familysupportcenter.org/services/lifestart-village','https://familysupportcenter.org/services','https://www.familysupportcenter.org/services-1'],'checklist-gap',email='info@familysupportcenter.org')

add('assist','ASSIST — Emergency Home Repair','218 E 500 S, Salt Lake City, UT 84111','801-355-7085','https://assistutah.org/services/emergency-home-repair',[4],[],
    'Repairs to serious home safety problems, including plumbing, heating, electrical and accessibility problems.',
    'Generally homeowners below 80% of area median income in participating Salt Lake County jurisdictions; renters only in very limited hazardous situations.',
    'Low-income residents whose housing needs urgent safety repairs.',
    'Call with the repair problem, city, household size, income and ownership information. Preferred calling times are weekdays 8–9 am or 1–2 pm.',
    'Staff check location, documents and eligibility before arranging work; not all repairs or county municipalities qualify.',
    'Adds a practical repair route so an unsafe home does not automatically become a move or shelter problem.',
    ['https://assistutah.org/services/emergency-home-repair','https://www.sslc.gov/519/Housing-Resources'],'south-salt-lake-list',hours='Preferred phone times Monday–Friday 8–9 am or 1–2 pm')

add('habitat-repair','Habitat for Humanity Greater Salt Lake Area — Critical Home Repairs','1276 South 500 West, Salt Lake City, UT 84101','801-263-0136 ext. 211','https://habitatsaltlake.org/our-programs/critical-home-repairs',[4],[],
    'Critical roof, plumbing, electrical, heating and accessibility repairs.',
    'Low-to-moderate income owners of homes on permanent foundations in Salt Lake, Davis or Tooele counties; citizenship or legal residency required.',
    'Homeowners who need essential safety repairs.',
    'Use the Critical Home Repair application or call extension 211 about eligibility.',
    'Assistance can involve grants or a deferred loan due when ownership changes; confirm the terms and project availability.',
    'Adds another repair provider with a broader three-county area and grant/deferred-loan options when ASSIST is not a fit.',
    ['https://habitatsaltlake.org/our-programs/critical-home-repairs'],'county-list')

add('slc-repair','Salt Lake City — Fix Your Home','451 S State Street, Room 445, Salt Lake City, UT 84111','801-535-7233','https://www.slc.gov/housingstability/fix-your-home/',[4],['seniors','disabilities'],
    'City funding for minor repairs and larger health, safety or structural home repairs.',
    'Low-income Salt Lake City households; the minor-repair grant specifically serves seniors or people with disabilities.',
    'Eligible city homeowners, with a targeted minor-repair option for older or disabled residents.',
    'Use the city’s Minor Repairs or Home Repairs application, or call for help choosing.',
    'Major repairs may use a loan. Fix the Bricks is closed; do not apply expecting seismic-retrofit funding. Confirm available funding and terms.',
    'Adds city repair financing and a targeted minor-repair grant when the nonprofit repair options do not fit.',
    ['https://www.slc.gov/housingstability/fix-your-home/'],'official-list-followup',
    duplicate='One repair-agency record; minor and major repair choices explained together. Separate from CDCU-operated Tenant Resource Center with different intake and eligibility.')

add('cdcu-homebuyer','CDCU — homebuyer coaching and down-payment assistance','501 East 1700 South, Salt Lake City, UT 84105','801-994-7222','https://cdcutah.org/i-want-to/homestart',[5],[],
    'Homebuyer education, individual housing counseling and assessment for down-payment assistance.',
    'Coaching is available to people preparing to buy; assistance has additional first-time buyer, income, occupancy and contribution requirements.',
    'People planning a home purchase, including households not yet ready for a mortgage.',
    'Call CDCU for counseling or follow its registration/intake links. Ask about the next class rather than relying on past advertised dates.',
    'Financial assistance is limited and can be a repayable deferred loan. Coaching does not guarantee a loan, grant or home.',
    'Covers homebuying readiness and assistance screening through a local housing counselor.',
    ['https://cdcutah.org/i-want-to/homestart','https://cdcutah.org/i-want-to/seek-down-payment-assistance'],'211-list',
    duplicate='One CDCU homebuyer record. Its renter center remains separate because clients encounter different phone, intake and city eligibility.')

add('ssvf','The Road Home — Supportive Services for Veteran Families','Salt Lake County; direct outreach contact','385-977-2920','https://theroadhome.org/ssvf-referral/',[6],['veterans'],
    'Veteran housing-stability assessment, homelessness prevention and rehousing support.',
    'Veterans facing homelessness; the provider limits prevention assistance to Salt Lake County residents and screens other program criteria.',
    'Veterans and their households needing housing help.',
    'Call or email the SSVF outreach team directly to arrange a meeting. Ask which community walk-in location is appropriate.',
    'Some outreach sessions are residents-only, but the flyer also offers public sessions and appointments. Ask about alternate documents if identification or income paperwork is missing.',
    'Adds veteran-specific housing help with a public outreach route, without requiring a veteran already to live in a shelter.',
    ['https://theroadhome.org/ssvf-referral/','https://theroadhome.org/wp-content/uploads/2025/12/SSVF-Outreach-Flyer-5.2025.pdf'],'county-list-followup',email='veterans@theroadhome.org')

add('rental-search','AffordableHousing.com — Salt Lake City rental search','Online; Salt Lake City listings','','https://www.affordablehousing.com/salt-lake-city-ut/',[8],[],
    'Searchable rental listings and property contact routes.',
    'Anyone may browse; landlords and individual housing programs set their own screening and application requirements.',
    'People comparing available rental options in Salt Lake City.',
    'Open the Salt Lake City search and contact the listed property about rent, eligibility and availability.',
    'A listing is not a vacancy guarantee or a subsidy award. Confirm fees and terms directly; the site also promotes optional paid features.',
    'Covers self-directed rental searching, distinct from applying to a housing-authority waiting list.',
    ['https://www.affordablehousing.com/salt-lake-city-ut/','https://www.affordablehousing.com/housing-authority-ut/housing-connect-348/'],'official-authority-link')

add('woodspring','WoodSpring Suites Bluffdale Salt Lake City — extended stay','1478 West 14000 South, Bluffdale, UT 84065','385-243-1064','https://www-media.woodspring.com/extended-stay-hotels/locations/utah/bluffdale/woodspring-suites-bluffdale-salt-lake-city',[8],[],
    'Paid extended-stay rooms with a kitchen, including weekly and longer stays.',
    'Guests must meet the hotel’s booking and payment conditions; ask about identification, deposits and total charges.',
    'People able to pay for temporary lodging in southern Salt Lake County.',
    'Call the hotel for a complete quote and booking terms before traveling to Bluffdale.',
    'Commercial lodging, not rental assistance or free shelter. Upfront payment, transportation and pet charges can make it unsuitable; prices vary.',
    'Adds a directly bookable temporary lodging option for someone who can pay and reach Bluffdale while seeking a rental.',
    ['https://www-media.woodspring.com/extended-stay-hotels/locations/utah/bluffdale/woodspring-suites-bluffdale-salt-lake-city','https://www.woodspring.com/extended-stay-hotels/locations/utah/salt-lake-city/hotels'],'checklist-gap')

add('ruff-haven','Ruff Haven — crisis sheltering for pets','264 S Glendale Street, Suite 100, Salt Lake City, UT 84104','801-251-6765','https://www.ruffhaven.org/apply',[9],[],
    'Temporary care for dogs and cats while their owners face a crisis.',
    'Utah pet owners with an unexpected crisis such as eviction, homelessness, hospitalization or domestic violence; apply for screening.',
    'People who risk losing their pets while resolving an emergency.',
    'Apply online; text the sheltering number with questions. Intake and visits require appointments.',
    'No required sheltering fee. Published durations differ; agree the stay and reunification plan with staff. This shelters pets, not people, and acceptance is not guaranteed.',
    'Addresses a housing barrier the human-housing providers do not solve: keeping a pet safe during displacement.',
    ['https://www.ruffhaven.org/apply','https://www.ruffhaven.org/faqs','https://www.ruffhaven.org/programs','https://www.ruffhaven.org/what-we-do'],'checklist-gap',email='info@ruffhaven.org',hours='By appointment; not a 24-hour facility')

add('uca-mediation','Utah Community Action — landlord–tenant mediation','Salt Lake County residents may contact the statewide service','801-214-3109','https://utahca.org/case-management-housing/',[10],[],
    'Mediation to help landlords and tenants resolve housing disputes.',
    'Tenants or landlords can request help; tenants with a three-day pay-or-vacate notice can use the tenant application.',
    'Renters and landlords seeking to preserve a tenancy.',
    'Call the mediation line or use the tenant application linked on UCA’s housing page.',
    'Mediation is not legal advice or representation and does not itself extend a deadline.',
    'Adds direct dispute resolution to the starter navigator and rent-help routes.',
    ['https://utahca.org/case-management-housing/','https://www.slc.gov/access-belonging/wp-content/uploads/sites/57/2026/01/2025-07_CommunityResourceGuide-WebReady_01-26-1.pdf'],'city-guide',
    duplicate='Separate UCA program justified by distinct mediation intake and phone, not another listing of rental aid.',email='mediation@utahca.org')

add('homeinn','A Tall Order Foundation / HomeInn — transitional rooms','Outreach: 428 W 300 S, Salt Lake City, UT 84101','801-965-8628','https://www.atallorder.org/foundation',[3],[],
    'Low-cost single-room transitional housing with shared kitchen and common facilities.',
    'Guests must qualify through HomeInn and follow housing rules; ask about screening and suitability before visiting.',
    'People moving out of homelessness who can pay rent and live in a single-room setting.',
    'Call or contact the downtown outreach office for an application conversation and current openings.',
    'The website publishes entry rent of $510 including utilities; confirm current rent, extra fees and availability. This is paid transitional housing, not emergency shelter or a verified fixed-income shared-housing program.',
    'Adds a low-cost single-room route for adults, materially different from LifeStart’s single-parent family apartments.',
    ['https://www.atallorder.org/foundation','https://www.atallorder.org/rates','https://www.atallorder.org/contact'],'checklist-gap',email='atallorderfoundation@gmail.com')

# Service-area descriptions must not masquerade as geocodable street addresses.
street_keys={'tenant-center','assist','habitat-repair','slc-repair','cdcu-homebuyer','woodspring','ruff-haven'}
for row in rows:
    row['address']=row['where'] if row['key'] in street_keys else ''
    if row['key']=='homeinn': row['address']='428 W 300 S, Salt Lake City, UT 84101 (outreach office)'
(ROOT/'curation'/'prepared-drafts.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
print(f'Wrote {len(rows)} authored drafts')
