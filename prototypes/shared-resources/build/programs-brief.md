# Front doors to federal programs that states run

For the shared-resources prototype's Coverage tab: for each state, which resources are its
**front door** to each federal program that states run (shared-resources brainstorm,
20 October 2026: these programs are state-level, with a way in per state).

The programs, by these exact names:

- **SNAP**: food stamps or nutrition assistance (Utah SNAP, Arizona Nutrition Assistance,
  Idaho Food Stamps, New Jersey SNAP, ...).
- **Medicaid**: the state's Medicaid (AHCCCS in Arizona, Turquoise Care or Centennial Care in
  New Mexico, NJ FamilyCare, Idaho Medicaid, Nevada Medicaid, Utah Medicaid).
- **CHIP**: children's health insurance (Utah CHIP, KidsCare in Arizona, NJ FamilyCare for
  children, Nevada Check Up, New Mexico's children's Medicaid/CHIP).
- **WIC**: Women, Infants and Children.
- **TANF**: cash assistance for families (Utah FEP, Arizona Cash Assistance, Idaho TAFI,
  New Mexico NM Works / cash assistance, Nevada TANF, New Jersey WorkFirst NJ).
- **LIHEAP**: home energy bill assistance (Utah HEAT, Arizona LIHEAP, Nevada Energy
  Assistance Program, New Jersey LIHEAP, ...).

## The test

A resource is a front door to a program when **a missionary could send a person there to
apply for or enrol in that program**: the state agency or its application portal
(Health-e-Arizona Plus, YES New Mexico, Access Nevada, idalink, myCase, NJ OneApp), a local
office of that agency, a county board of social services, a WIC clinic, a local agency that
takes LIHEAP applications, or a resource whose text gives the way to apply (a "SNAP overview
and application assistance" entry pointing to the state's application counts).

Not a front door: a clinic or provider that only **accepts** Medicaid, a food pantry, a
legal aid office that appeals denials, a general resource directory, or a resource that
merely mentions the program. A program for one tribe or one narrow group is still a front
door if people apply there (a tribal WIC clinic).

## Do

Read each resource's name, description and information. Give the programs, from the six
names above, it is a front door to; most will have none.

## Output

Write a JSON array to the output path you were given, one object per input resource, in
input order: `{"id": "...", "federalPrograms": ["SNAP", "Medicaid"]}` (an empty list when
none). Every input id exactly once. Validate the file parses as JSON with the same ids as the
input, and report only the count written, how many have any program, and any problems.
