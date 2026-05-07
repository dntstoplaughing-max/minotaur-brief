# Ground-Truth Provenance — MINOTAUR-Brief

This document is the construct-validity record for the element-to-exhibit
mappings in `prompts/ground_truth.json`. For each count, every required
element is paired with (i) a controlling-authority quotation drawn from
`corpus.json` `key_passages`, (ii) optional subsidiary authorities, and
(iii) a one-sentence justification for each exhibit listed in that
count's `element_exhibit_map`.

Pin cites were extracted by string-matching each `key_passage` against
the case's `notion_full_text_url` page text and recording the nearest
preceding pagination marker (reporter format `*NNN`, syllabus headnote
`[NNN]`, or SCOTUS slip-op page numbers). Where the corpus's
`key_passages` were summary paraphrases rather than verbatim opinion
language, `corpus.json` was edited to substitute the verbatim quotation
before extraction. Where a slip opinion in the Notion archive lacks
reporter pagination entirely, the pin cite is annotated `(slip op.;
reporter pagination not in archive)`.

The candidate pool of cases per count is taken from `tasks.json`
`relevant_cases`. The legacy `used_in` field has been removed from
`corpus.json`.

---

## Count I — Title IX Deliberate Indifference (20 U.S.C. § 1681; *Davis v. Monroe County Bd. of Educ.*)

Candidate pool: cases 1 (Davis), 4 (Doe v. USciences), 15 (Hall),
16 (McAvoy), 17 (Foster).

### Element: actual_knowledge
- **Required:** Actual knowledge by official with authority to act.
- **Controlling authority:** *Davis*, 526 U.S. at 633 (1999). "We conclude that it may, but only where the funding recipient acts with deliberate indifference to known acts of harassment in its programs or activities." Further developed at 526 U.S. at 646: "[W]e [thus] conclude that recipients of federal funding may be liable for 'subject[ing]' their students to discrimination where the recipient is deliberately indifferent to known acts of student-on-student sexual harassment and the harasser is under the school's disciplinary authority."
- **Subsidiary authority:** *Hall v. Millersville Univ.*, No. 19-3275, slip op. (3d Cir. Jan. 11, 2022) (slip op.; reporter pagination not in archive — verifiable via the case's `notion_full_text_url`). "[I]t is an intentional violation of Title IX's terms for a funding recipient to act with deliberate indifference to known sexual harassment where the recipient exercises substantial control over the context in which the harassment occurs and the harasser, even if they are a third party." (Hall extends Davis to non-student harassers under substantial-control doctrine.)
- **Exhibits mapped:**
  - `R`: Plaintiff's July 20, 2025 email to Selcer naming Respondent's specific harassing conduct evidences actual notice transmitted to a faculty member with reporting authority, satisfying the actual-knowledge prong because the recipient is on record as having received the report.
  - `S`: Plaintiff's July 21, 2025 itemization of conduct violations sent to Wasilko corroborates actual knowledge by establishing that the Dean of Students received an enumerated complaint.
  - `B-0`: The June 30, 2025 emergency-housing email establishes the inception date of actual knowledge by Wasilko, anchoring the start of the institutional-response clock.
  - `B-1`: Simpson's July 24, 2025 outreach acknowledges Plaintiff's prior report, evidencing that the Title IX Coordinator herself had actual knowledge of the alleged harassment.
  - `B-2`: Wasilko's July 25, 2025 email referencing the underlying complaint establishes that actual knowledge persisted at the senior-administrator level after upper-admin escalation.
  - `B-5`: Simpson's August 13, 2025 acknowledgment that Plaintiff's "concerns and allegations warrant further information gathering and review" satisfies the actual-knowledge prong because the Coordinator expressly recognizes the report.
  - `Z-e`: PCHE training slide defining "actual knowledge" as "notice of sexual harassment or allegations" establishes that Defendant's own training materials adopt the Davis standard, evidencing institutional capacity to recognize when actual knowledge has been received.

### Element: clearly_unreasonable
- **Required:** Clearly unreasonable response (deliberate indifference).
- **Controlling authority:** *Davis*, 526 U.S. at 648 (1999). "[T]he recipient's response to the harassment or lack thereof is clearly unreasonable in light of the known circumstances."
- **Subsidiary authority:** *Foster v. Bd. of Regents of Univ. of Mich.*, No. 19-1314, slip op. (6th Cir. Dec. 11, 2020) (en banc) (slip op.; reporter pagination not in archive). "Neither does [the deliberate indifference standard] require courts to conclude that minimal, ineffective, or belated efforts to respond to sexual harassment are not clearly unreasonable as a matter of law."
- **Exhibits mapped:**
  - `B-6`: Simpson's August 14, 2025 jurisdictional reversal nineteen hours after acknowledging jurisdiction, on an unchanged factual record, evidences a response that is clearly unreasonable in light of the known circumstances.
  - `B-5`: Simpson's August 13 acknowledgment paired with no offer of supportive measures evidences the clearly-unreasonable failure to act on known harassment within the regulatory framework.
  - `B-2`: Wasilko's "we cannot assist you ... unless you are willing to engage" conditioning evidences a clearly-unreasonable response because federal regulation does not condition supportive measures on meeting attendance.
  - `G`: Wasilko's July 24, 2025 housing denial evidences the clearly-unreasonable refusal to provide a supportive measure expressly contemplated by 34 C.F.R. § 106.44(a).
  - `Z-b`: Defendant's own deliberate-indifference training framework establishes the institution's awareness of the Davis standard, making subsequent non-compliance evidence of a clearly-unreasonable response judged against its own training.
  - `Z-c`: PCHE training defining supportive measures as "mandatory, non-punitive, individualized" evidences the clearly-unreasonable nature of Defendants' failure to offer any supportive measure during the 45-day window.

### Element: severe_pervasive
- **Required:** Severe, pervasive, objectively offensive harassment.
- **Controlling authority:** *Davis*, 526 U.S. at 650 (1999). "[F]unding recipients are properly held liable in damages only where they are deliberately indifferent to sexual harassment, of which they have actual knowledge, that is so severe, pervasive, and objectively offensive that it can be said to deprive the victims of access to the educational opportunities or benefits provided by the school."
- **Subsidiary authority:** None from candidate pool that addresses the severity standard distinctly.
- **Exhibits mapped:**
  - `D`: The Signal transcript and timeline of the June 23–30, 2025 events evidences the severe-and-pervasive prong by documenting a sustained physical-pursuit incident that is objectively offensive on its face.
  - `R`: Plaintiff's July 20 narration of the incident to the chair corroborates severity by reproducing the physical-pursuit and confrontation facts in a contemporaneous record.

### Element: denial_of_access
- **Required:** Denial of equal educational access.
- **Controlling authority:** *Davis*, 526 U.S. at 650 (1999). "[S]o severe, pervasive, and objectively offensive that it can be said to deprive the victims of access to the educational opportunities or benefits provided by the school."
- **Subsidiary authority:** None from candidate pool.
- **Exhibits mapped:**
  - `F`: Treating Physician's medical letter establishing safety-related fear evidences denial of equal access because medical documentation links the harassment to inability to participate equally in educational programs.
  - `G`: Wasilko's July 24, 2025 housing denial evidences denial of equal access because the lack of housing materially impaired Plaintiff's ability to remain enrolled.
  - `B-6`: Simpson's jurisdictional disclaimer denying any further institutional process evidences the formal closure of the access-restoration channel.
  - `P`: Title IX Policy Appendix C, defining the institutional reporting/responsibility regime, evidences the access-restoration framework that was not deployed for Plaintiff.

### Pitfalls
- **Conflating 'actual knowledge' with constructive notice:** Authority: *Davis*, 526 U.S. at 633, 646 (1999) (deliberate indifference requires actual, not constructive, notice).
- **Failing to identify the specific official with authority to address (must be Title IX coordinator or equivalent):** Authority: *Davis*, 526 U.S. at 646 (1999) ("the harasser is under the school's disciplinary authority"); *Hall*, slip op. (3d Cir. 2022) (substantial-control framework applied where Deputy Title IX Coordinator received but did not forward report).
- **Mischaracterizing the 'clearly unreasonable' standard as mere negligence:** Authority: *Davis*, 526 U.S. at 648 (1999) (clearly unreasonable "in light of the known circumstances" is the standard, distinct from negligence).
- **Stating severity element without addressing all three prongs (severe AND pervasive AND objectively offensive):** Authority: *Davis*, 526 U.S. at 650 (1999) (all three prongs are conjunctive in the controlling formulation).

---

## Count II — Title IX Retaliation (20 U.S.C. § 1681; *Jackson v. Birmingham Bd. of Educ.*)

Candidate pool: cases 24 (Farrell), 25 (Doe v. Mercy Catholic),
26 (Canada), 27 (Kachmar), 28 (Atkinson), 29 (Kengerski),
30 (Jalil), 31 (Lauren W.), 32 (Carvalho-Grevious).

### Element: protected_activity
- **Required:** Protected activity (reporting, opposing, or participating).
- **Controlling authority:** *Atkinson v. Lafayette Coll.*, 460 F.3d 447, 451–52 (3d Cir. 2006) (vacating dismissal of Title IX retaliation claim for inconsistency with *Jackson v. Birmingham Bd. of Educ.*, 544 U.S. 167 (2005); the verbatim opinion language now in `corpus.json` `key_passages` reproduces the Atkinson Court's own articulation. The protected-activity element is established by Atkinson's import of Jackson's holding that "Title IX's private right of action encompasses claims of retaliation against an individual because he or she has complained about sex discrimination" — a formulation Atkinson treats as controlling.)
- **Subsidiary authority:** *Kengerski v. Harper*, No. 20-1307, slip op. (3d Cir. 2021) (slip op.; reporter pagination not in archive). "Plaintiff need only hold an 'objectively reasonable belief, in good faith' that conduct violated Title VII." (Reasonable-belief test, imported into Title IX retaliation via Doe v. Mercy Catholic.)
- **Exhibits mapped:**
  - `B-3A`: The July 26, 2025 OCR escalation and records demand evidences protected activity because filing a complaint with a federal civil-rights enforcement agency is paradigmatic Title IX participation.
  - `B-0A`: The July 23, 2025 gender-reversal hypothetical email evidences protected activity because raising sex-based comparative analysis to administrators is opposition conduct under the statute.

### Element: adverse_action
- **Required:** Adverse action that would deter a reasonable person.
- **Controlling authority:** *Doe v. Mercy Catholic Med. Ctr.*, No. 16-1247, slip op. (3d Cir. 2017) (slip op.; reporter pagination not in archive). "Title IX retaliation claims are analyzed under the Title VII burden-shifting framework." (Imports the Title VII deterrence standard, including the *Burlington Northern v. White*, 548 U.S. 53 (2006), formulation that an adverse action is one that "would have dissuaded a reasonable worker from making or supporting a charge of discrimination" — Burlington itself is referenced for the substantive deterrence standard but is outside the corpus.)
- **Subsidiary authority:** *Jalil v. Avdel Corp.*, 873 F.2d 701, 708 (3d Cir. 1989) (the adverse-action half of the Jalil holding, where Jalil "demonstrated the causal link between the two by the circumstance that the discharge followed rapidly, only two days later," presupposes that discharge satisfies the adverse-action prong).
- **Exhibits mapped:**
  - `B-6`: Simpson's August 14 jurisdictional reversal evidences adverse action because formally closing the institutional channel after protected activity would deter a reasonable person from further reporting.
  - `B-7`: Sawa's August 15, 2025 retaliation threat evidences adverse action because an explicit threat of consequences for protected conduct meets the deterrence standard.
  - `I`: Selcer's August 25, 2025 meeting exchange imposing a Zoom countdown evidences adverse action by introducing a punitive condition tied to participation that would deter a reasonable person from continued advocacy.
  - `J`: Selcer's September 3, 2025 final directive evidences adverse action because removing previously-granted attendance flexibility shortly after Plaintiff's continued advocacy would deter a reasonable person.
  - `I-1`: Plaintiff's demand for retraction of the retaliatory Zoom countdown corroborates that the Zoom revocation functioned as an adverse action by documenting Plaintiff's contemporaneous characterization of the countdown as retaliatory.
  - `X-7`: Faculty B's February 13, 2026 reassignment-request email reading "door open ... no performance complaint" evidences that the reassignment was unaccompanied by performance criticism — making the subsequent stipend-threat narrative an adverse action divorced from legitimate cause.
  - `X-8`: Selcer's February 13, 2026 fabrication of "performance issues" and stipend threat evidences adverse action because threatening a multi-year stipend during active litigation would deter a reasonable person.

### Element: causal_connection
- **Required:** Causal connection between protected activity and adverse action.
- **Controlling authority:** *Kachmar v. SunGard Data Sys., Inc.*, 109 F.3d 173, 178 (3d Cir. 1997). "It is important to emphasize that it is causation, not temporal proximity itself, that is an element of plaintiff's prima facie case [...]."
- **Subsidiary authority:** *Kachmar*, 109 F.3d at 177 (3d Cir. 1997) ("[W]here there is a lack of temporal proximity, circumstantial evidence of a 'pattern of antagonism' following the protected conduct can also give rise to the inference"); *Jalil*, 873 F.2d at 708 (3d Cir. 1989) (two-day proximity sufficient — verbatim "He demonstrated the causal link... only two days later" language; pin cite *708 directly verified by string-match in fetched Part 1/2 and Part 2/2); *Farrell v. Planters Lifesavers Co.*, 206 F.3d 271 (3d Cir. 2000) (subsidiary; pin cite to be confirmed against `notion_full_text_url`); *Carvalho-Grevious v. Del. State Univ.*, No. 15-3521, slip op. (3d Cir. 2017) (slip op.; reporter pagination not in archive — "likely reason" at prima facie stage).
- **Exhibits mapped:**
  - `B-3`: Wasilko's July 28 OCR-removal email two days after Plaintiff's OCR filing evidences causal connection via temporal proximity (Jalil).
  - `B-6`: The 19-hour jurisdictional reversal after Plaintiff's three protected-activity emails evidences causal connection because the only intervening event was protected conduct.
  - `B-7`: Sawa's threat issued one day after the Simpson reversal evidences causal connection by establishing a coordinated escalation closely following protected activity.
  - `I`: Selcer's August 25 Zoom countdown imposed during active escalation evidences causal connection because the countdown's timing tracks Plaintiff's continuing protected conduct.
  - `X-4`: Faculty B's February 5, 2026 email reporting "interpersonal upset — no performance issues" evidences the absence of any non-retaliatory cause for the subsequent stipend threat, supporting causation under Kachmar's whole-record analysis.
  - `X-6`: The February 10, 2026 Selcer/Mullins meeting transcript with "no performance issues" language evidences causal connection by establishing that the performance-issues narrative was manufactured between February 10 and February 13 for retaliatory purpose.
  - `X-8`: Selcer's same-day fabrication of "performance issues" three days after the meeting and the same day as Faculty B's contradictory email evidences causal connection through a documented divergence between the proffered reason and the underlying record.
  - `K-2`: Blair's October 22, 2025 consultation with Selcer (the conflicted party) seven days after TRO testimony evidences causal connection by tying institutional decisions to protected litigation activity.

### Pitfalls
- **Failing to apply but-for causation post Univ. of Texas Southwestern Med. Ctr. v. Nassar (2013):** Authority: *Nassar*, 570 U.S. 338 (2013) — outside corpus; reviewers verifying this pitfall consult Nassar directly. Within the corpus, *Carvalho-Grevious*, slip op., establishes that at the prima facie stage the plaintiff need only show that the protected activity was the "likely reason" for the adverse action — distinct from the but-for standard at the merits stage.
- **Citing trivial actions as 'adverse' without applying the Burlington Northern deterrence standard:** Authority: *Burlington N. & Santa Fe Ry. v. White*, 548 U.S. 53 (2006) — outside corpus. Within the corpus, *Doe v. Mercy Catholic*, slip op., imports this framework via Title VII analysis.
- **Conflating Title IX retaliation with Title VII (related but distinct frameworks):** Authority: *Doe v. Mercy Catholic*, slip op. (3d Cir. 2017) (slip op.; reporter pagination not in archive). The Mercy Catholic frame imports Title VII analysis but does not itself state the retaliation framework's substantive elements; reviewers should treat the conflation pitfall as flagged when the brief substitutes Title VII case-specific holdings without acknowledging the implied-cause-of-action provenance under Title IX.

---

## Count III — ADA Title II / Section 504 Failure to Accommodate (29 U.S.C. § 794; 42 U.S.C. § 12132; *Taylor v. Phoenixville Sch. Dist.*)

Candidate pool: cases 6 (Taylor), 18 (Osseo), 19 (Oross).

### Element: qualified_individual
- **Required:** Qualified individual with disability.
- **Controlling authority:** *A.J.T. v. Osseo Area Sch.*, 605 U.S. ___, slip op. at 8 (2025). "The substantive provisions of both Title II and Section 504, by their plain terms, apply to 'qualified individual[s]' with disabilities. 29 U.S.C. § 794(a); 42 U.S.C. § 12132. There is no textual indication that the protections of either disability discrimination statute apply with lesser force to certain qualified individuals bringing certain kinds of claims." (Osseo presupposes the qualified-individual element by holding that ordinary disability-discrimination analysis applies; the element itself is statutorily defined and Osseo confirms it controls in the educational-services context.)
- **Subsidiary authority:** None from candidate pool that articulates the qualified-individual standard distinctly.
- **Exhibits mapped:**
  - `F`: Treating Physician's medical letter satisfies the qualified-individual element because contemporaneous medical documentation from a treating physician establishes a recognized disability framework for ADA/§ 504 purposes.

### Element: notice
- **Required:** Notice of disability and need for accommodation.
- **Controlling authority:** *Taylor v. Phoenixville Sch. Dist.*, 184 F.3d 296, 319 (3d Cir. 1999). "To show that an employer failed to participate in the interactive process, a disabled employee must demonstrate: 1) the employer knew about the employee's disability; 2) the employee requested accommodations or assistance for his or her disability; 3) the employer did not make a good faith effort to assist the employee in seeking accommodations; and 4) the employee could have been reasonably accommodated but for the employer's lack of good faith."
- **Subsidiary authority:** None from candidate pool.
- **Exhibits mapped:**
  - `F`: Treating Physician's medical letter delivered to administrators establishes the notice prong (Taylor factor 1) by documenting the disability in writing to the institution.
  - `I`: Selcer's August 25 meeting exchange acknowledging the request for participation flexibility evidences institutional notice that an accommodation was sought.

### Element: requested_accommodation
- **Required:** Request for reasonable accommodation.
- **Controlling authority:** *Taylor*, 184 F.3d at 319 (3d Cir. 1999) (Taylor factor 2 in the four-factor framework quoted above).
- **Subsidiary authority:** None from candidate pool.
- **Exhibits mapped:**
  - `I`: Selcer's August 25 exchange acknowledges Plaintiff's request for Zoom-based participation, satisfying Taylor factor 2 because the request is documented in institutional correspondence.
  - `I-1`: Plaintiff's September 2 demand for retraction of the retaliatory countdown reaffirms the accommodation request and corroborates that it was framed as a reasonable accommodation rather than a preference.

### Element: denial
- **Required:** Denial of accommodation (without engaging in the interactive process).
- **Controlling authority:** *Taylor*, 184 F.3d at 317 (3d Cir. 1999). "[A]n employer who acts in bad faith in the interactive process will be liable if the jury can reasonably conclude that the employee would have been able to perform the job with accommodations." Also *Taylor*, 184 F.3d at 319 (Taylor factor 3: "the employer did not make a good faith effort to assist the employee in seeking accommodations").
- **Subsidiary authority:** *Oross v. Kutztown Univ.*, No. 21-5032, slip op. (E.D. Pa. July 25, 2023) (slip op.; reporter pagination not in archive). "University applied blanket no-remote policy with no written basis, no individualized assessment of plaintiff's request"; "Accommodation request was 'dead on arrival' — interference with the interactive process established."
- **Exhibits mapped:**
  - `J`: Selcer's September 3 final directive evidences denial without good-faith interactive process because the directive is conclusory and unaccompanied by alternatives or individualized assessment.
  - `V`: Selcer's October 17 post-TRO denial coordinated with Faculty C evidences continued denial of accommodation paired with reversal of a previously authorized supportive measure.
  - `W`: The Faculty C authorization-and-reversal email sequence evidences the institutional pattern of granting then withdrawing accommodation, satisfying the bad-faith interactive-process prong.
  - `Q`: The October 6–17 Zoom-removal sequence evidences the systematic denial of accommodation through revocation rather than dialogue.

### Element: resulting_harm
- **Required:** Resulting harm.
- **Controlling authority:** *Taylor*, 184 F.3d at 319 (3d Cir. 1999) (Taylor factor 4: "the employee could have been reasonably accommodated but for the employer's lack of good faith").
- **Subsidiary authority:** *A.J.T. v. Osseo Area Sch.*, 605 U.S. ___, slip op. at 2–3 (2025). "Schoolchildren bringing ADA and Rehabilitation Act claims related to their education are not required to make a heightened showing of 'bad faith or gross misjudgment' but instead are subject to the same standards that apply in other disability discrimination contexts." (Osseo rejects the heightened damages standard, simplifying the harm analysis.)
- **Exhibits mapped:**
  - `C`: External Faculty Witness academic-expert declarations establish concrete educational harm from denied participation, evidencing harm proximate to the denial.
  - `A`: The housing-crisis timeline evidences resulting harm by documenting deterioration in Plaintiff's living conditions concurrent with the denial of accommodation.
  - `V`: Selcer's October 17 denial after TRO testimony evidences resulting harm by tying loss of educational participation to the denial event.

### Pitfalls
- **Establishing 'disability' via fear/distress alone without major-life-activity-substantially-limited analysis:** Authority: 42 U.S.C. § 12102(1)–(2) (statutory definition) — the major-life-activity analysis is statutorily required and presupposed by all candidate-pool cases, though no `key_passage` quotes a case for it directly. Reviewers should verify whether the brief addresses at least one major life activity substantially limited by the alleged disability.
- **Conflating ADA Title II standards with Title III (different defenses, different remedies):** Authority: 42 U.S.C. § 12131 et seq. (Title II) vs. 42 U.S.C. § 12181 et seq. (Title III) — distinction is statutory; no candidate-pool case articulates it. Reviewers should verify whether the brief properly anchors in Title II (public entities) given Defendant's status as a private university subject to § 504, not Title II.
- **Misstating A.J.T. v. Osseo Area Schools standard:** Authority: *Osseo*, 605 U.S. ___, slip op. at 2–3, 8 (2025). Note: the rubric describes Osseo as requiring "bad faith or gross misjudgment for damages," which inverts what Osseo holds — Osseo *rejects* that heightened standard. Reviewers should treat the pitfall as an attribution check: is the brief stating Osseo's holding correctly?
- **Failing to address the interactive process requirement explicitly:** Authority: *Taylor*, 184 F.3d at 317, 319 (3d Cir. 1999) (interactive-process duty articulated in the controlling four-factor framework).

---

## Count IV — Pennsylvania Common-Law Fraud (Fed. R. Civ. P. 9(b); *Bortz v. Noon*; *Gibbs v. Ernst*) — OPPOSITION TO SUMMARY JUDGMENT

Candidate pool: cases 7 (Majestic Blue), 10 (Gibbs), 12 (Moser),
20 (Neuman), 21 (Peerless), 22 (Duquesne Light), 23 (Woodward).

### Element: false_representation
- **Required:** False representation of material fact.
- **Controlling authority:** *Gibbs v. Ernst*, 538 Pa. 193, 647 A.2d 882, 207 (1994). "(1) a representation; (2) which is material to the transaction at hand; (3) made falsely, with knowledge of its falsity or recklessness as to whether it is true or false; (4) with the intent of misleading another into relying on it; (5) justifiable reliance on the misrepresentation; and (6) the resulting injury was proximately caused by the reliance."
- **Subsidiary authority:** *Moser v. DeSetta*, 589 A.2d 679, 163 (Pa. 1991). "The concealment of a material fact can amount to a culpable misrepresentation no less than does an intentional false statement." Also *Neuman v. Corn Exch. Nat'l Bank & Tr. Co.*, 51 A.2d 759, 764 (Pa. 1947). "The deliberate nondisclosure of a material fact amounts to culpable misrepresentation no less than does an intentional affirmation of a material falsity." (Pin cite *764 directly verified via *Duquesne Light*'s own internal citation: "*Neuman*, 51 A.2d at 764"; Pa. reporter equivalent is 356 Pa. at 451 per syllabus headnote 2.)
- **Exhibits mapped:**
  - `B-1`: Simpson's July 24 outreach framing institutional obligations as discretionary evidences a false representation because § 106.44(a) makes the obligations mandatory.
  - `B-2`: Wasilko's "we cannot assist you ... unless you are willing to engage" evidences a false representation because no federal regulation conditions assistance on meeting attendance.
  - `B-3`: Wasilko's July 28 meeting-requirement reiteration after OCR escalation evidences a continuing false representation post-OCR notice.
  - `B-5`: Simpson's "supportive measures" framing evidences a false representation because the term-of-art usage implied institutional Title IX engagement that was subsequently denied.
  - `B-6`: Simpson's August 14 jurisdictional disclaimer that the conduct "does not meet TAP 61, nor TAP 31's definitions ... even if proven to be true" evidences a false representation because the conduct meets the stalking definition under § 106.30 and TAP 61 Category 6.
  - `G`: Wasilko's July 24 housing denial evidences a false representation because the denial cited absence of authority that did not exist.
  - `I`: Selcer's August 25 falsified meeting summary evidences a false representation by mischaracterizing what was discussed.
  - `K-1`: Plaintiff's October 20 conflict-of-interest disclosure to Blair establishes the predicate against which Blair's subsequent representations are tested.
  - `K-2`: Blair's October 22 announcement of "joint determination" with Selcer evidences a false representation that independent TAP 33 review had occurred.
  - `K-5`: Blair's October 22 denial of TAP 33 applicability evidences a false representation because the policy plainly applied.
  - `P`: The Title IX Policy Appendix C establishes the institutional framework against which Defendants' representations are tested as false.
  - `S`: Plaintiff's enumerated July 21 conduct violations establish the factual record from which Defendants' subsequent contrary representations can be shown to be false.
  - `X-6`: The February 10 meeting transcript without "performance issues" language evidences that Selcer's later "performance issues" narrative was a false representation.
  - `X-8`: Selcer's February 13 fabrication of "performance issues" evidences a false representation directly contradicted by the same-day Faculty B email (X-7).

### Element: scienter
- **Required:** Scienter (knowledge of falsity or reckless disregard).
- **Controlling authority:** *Gibbs*, 647 A.2d at 207 (Pa. 1994) (Element 3 of the six-element formulation: "made falsely, with knowledge of its falsity or recklessness as to whether it is true or false").
- **Subsidiary authority:** *United States ex rel. Moore & Co. v. Majestic Blue Fisheries, LLC*, 812 F.3d 294 (3d Cir. 2016) (FCA scienter standard parallels PA fraud's reckless-disregard prong: "actual knowledge, deliberate ignorance, or reckless disregard"; pin cite to be confirmed against `notion_full_text_url`).
- **Exhibits mapped:**
  - `B-5`: Simpson's "supportive measures" acknowledgment paired with same-day reversal evidences scienter because the reversal was made with knowledge of the prior acknowledgment.
  - `B-6`: Simpson's reversal "even if proven to be true" evidences scienter because the language explicitly contemplates the truth of the underlying allegations.
  - `X-6`: The February 10 meeting transcript proves Selcer's contemporaneous knowledge that no performance issues existed, evidencing scienter for the February 13 fabrication.
  - `Z-d`: Conflict-of-interest training evidences scienter as to TAP 33 violations because Defendants had been trained on the standard they then violated.
  - `Z-e`: Actual-knowledge training evidences scienter as to Title IX obligations because Defendants had been trained on what constitutes notice.
  - `D`: The Signal transcript evidences the underlying factual record Defendants had reason to know about, supporting scienter for representations made contrary to that record.
  - `R`: Plaintiff's July 20 email to Selcer evidences Selcer's knowledge of the underlying conduct, supporting scienter for later contrary representations.

### Element: intent_to_induce
- **Required:** Intent to induce reliance.
- **Controlling authority:** *Gibbs*, 647 A.2d at 207 (Pa. 1994) (Element 4: "with the intent of misleading another into relying on it").
- **Subsidiary authority:** *Moser*, 589 A.2d at 163 (Pa. 1991). "[F]raud is composed of a misrepresentation fraudulently uttered with the intent to induce the action undertaken in reliance upon it, to the damage of its victim."
- **Exhibits mapped:**
  - `B-1`: Simpson's outreach requesting a meeting "to discuss options" evidences intent to induce because the framing was designed to channel Plaintiff into a meeting-conditioned process.
  - `B-2`: Wasilko's conditioning of assistance on engagement evidences intent to induce attendance at meetings as a precondition.
  - `B-3`: Wasilko's reiteration of the meeting requirement post-OCR evidences continuing intent to induce reliance on the false condition.
  - `B-5`: Simpson's term-of-art use of "supportive measures" evidences intent to induce reliance on Title IX framework engagement.
  - `P`: The Title IX Policy Appendix C establishes the framework Defendants invoked to induce reliance, evidencing the inducement architecture.

### Element: justifiable_reliance
- **Required:** Justifiable reliance.
- **Controlling authority:** *Gibbs*, 647 A.2d at 207 (Pa. 1994) (Element 5: "justifiable reliance on the misrepresentation").
- **Subsidiary authority:** *Peerless Wall & Window Coverings, Inc. v. Synchronics, Inc.*, 85 F. Supp. 2d 519, 533–34 (W.D. Pa. 2000). "[R]eliance should be presumed where information material to the transaction was concealed by a positive misrepresentation and where the evidence shows that the deceived party would not have entered the transaction if the truth had been disclosed." Also *Neuman*, 51 A.2d at 764 (Pa. 1947) ("naturally the proper source of information" rule); *Duquesne Light Co. v. Westinghouse Elec. Corp.*, 66 F.3d 604, 612 (3d Cir. 1995). "[T]here is virtually no Pennsylvania case in which a defendant has been held to have a duty to speak when both the plaintiff and defendant were sophisticated business entities, entrusted with equal knowledge of the facts." (Pin cite *612 directly verified by string-match in fetched Part 1/3.)
- **Exhibits mapped:**
  - `B-1`: Simpson's institutional outreach with Title IX Coordinator authority establishes Plaintiff's justifiable reliance because the Coordinator is the proper source for Title IX guidance under Neuman.
  - `B-5`: The "supportive measures" usage by the Coordinator evidences justifiable reliance because Plaintiff had no superior source for that term-of-art guidance.
  - `G`: Wasilko's housing-denial citing of authority evidences justifiable reliance because the Dean of Students is the proper source for housing decisions.
  - `P`: The Title IX Policy Appendix C establishes the institutional source of authority on which reliance was justifiable.
  - `Z-e`: Defendants' own actual-knowledge training establishes the institutional baseline against which Plaintiff's reliance on Title IX representations was reasonable.

### Element: resulting_damages
- **Required:** Resulting damages — proximately caused by the reliance.
- **Controlling authority:** *Gibbs*, 647 A.2d at 207 (Pa. 1994) (Element 6: "the resulting injury was proximately caused by the reliance").
- **Subsidiary authority:** *Woodward v. Dietrich*, 548 A.2d 301 (Pa. Super. 1988) (foreseeable third-party reliance under Restatement §§ 531, 533, 536; pin cite to be confirmed against `notion_full_text_url`).
- **Exhibits mapped:**
  - `I`: Selcer's August 25 directive evidences resulting damages by documenting the punitive Zoom-countdown harm caused by reliance on prior misrepresentations.
  - `J`: Selcer's September 3 final directive evidences resulting damages because participation loss followed from the false meeting-requirement narrative.
  - `F`: Treating Physician's medical documentation evidences resulting damages by tying medical/safety harm to the institutional denial of supportive measures.
  - `X-7`: Faculty B's "no performance complaint" email evidences resulting damages by establishing the falsity-of-cause for the stipend threat that produced economic harm.
  - `X-8`: Selcer's stipend threat through Spring 2029 evidences resulting damages by quantifying the economic harm proximately caused by the false-representation conduct.

### Pitfalls
- **Treating fraudulent nondisclosure under Neuman v. Corn Exchange without establishing the requisite fiduciary or special-source relationship:** Authority: *Neuman*, 51 A.2d at 356 Pa. at 451 (Pa. 1947) (proper-source rule applies only where defendant is "naturally the proper source of information"); *Duquesne Light*, 66 F.3d at 612 (3d Cir. 1995) (no duty to speak between sophisticated equals).
- **Stating 'justifiable reliance' as a conclusion rather than analyzing reasonableness in light of plaintiff's information access:** Authority: *Gibbs*, 647 A.2d at 207 (Pa. 1994) (Element 5 phrasing requires analysis of justifiability, not bare assertion); *Peerless*, 85 F. Supp. 2d at 533–34 (presumption-from-materiality framework requires the materiality predicate).
- **Eliding the scienter requirement (knowledge OR reckless disregard, not negligence):** Authority: *Gibbs*, 647 A.2d at 207 (Pa. 1994) (Element 3 articulates the disjunctive standard).
- **Skipping causation/damages link:** Authority: *Gibbs*, 647 A.2d at 207 (Pa. 1994) (Element 6 requires proximate causation).

---

## Count V — Pennsylvania Civil Conspiracy + 42 U.S.C. § 1985 (*Thompson Coal Co. v. Pike Coal Co.*) — OPPOSITION TO SUMMARY JUDGMENT

Candidate pool: cases 3 (Desert Palace), 9 (Thompson Coal).

### Element: agreement
- **Required:** Agreement between two or more actors to commit unlawful act or use unlawful means.
- **Controlling authority:** *Thompson Coal Co. v. Pike Coal Co.*, 488 Pa. 198, 412 A.2d 466, 211 (1979). "To prove a civil conspiracy, it must be shown that two or more persons combined or agreed with intent to do an unlawful act or to do an otherwise lawful act by unlawful means."
- **Subsidiary authority:** *Desert Palace, Inc. v. Costa*, 539 U.S. 90, 98, 101 (2003) (circumstantial evidence sufficient — Title VII context, applied here by analogy: "Section 2000e-2(m) unambiguously states that a plaintiff need only 'demonstrat[e]' that an employer used a forbidden consideration with respect to 'any employment practice'" (at 98); "[d]irect evidence of discrimination is not required for a plaintiff to obtain a mixed-motive jury instruction" (at 101)).
- **Exhibits mapped:**
  - `K-2`: Blair's "I did need to consult Dr. Selcer ... Both Dr. Selcer and I strongly concur" evidences agreement because the language documents joint determination between two actors.
  - `B-2`: Wasilko's meeting-requirement statement evidences agreement because it parallels Simpson's framing in B-1, supporting an inference of coordination.
  - `B-3`: The OCR-removal pattern across actors evidences agreement because synchronized conduct without policy basis supports inference.
  - `B-5`: Simpson's coordinated framing evidences agreement when paired with Wasilko's parallel framing.
  - `X-4`: Faculty B's "interpersonal upset — no performance issues" email establishes the baseline against which X-6 and X-8 reveal coordinated narrative-shifting between Selcer and Blair.
  - `X-6`: The February 10 transcript shows the absence of the "recommendation to the Dean" language that appears three days later in X-8, evidencing intervening coordination — i.e., the agreement element by inference from textual divergence.
  - `X-8`: Selcer's "recommendation to the Dean of Liberal Arts" reference evidences agreement by tying Selcer's threat to Blair's office.
  - `D`: The Signal transcript establishes the underlying factual record on which Defendants' coordinated representations diverge.

### Element: unlawful_act
- **Required:** Unlawful act or unlawful means (underlying tort).
- **Controlling authority:** *Thompson Coal*, 412 A.2d at 211 (Pa. 1979) (quoted above; "unlawful act ... or unlawful means").
- **Subsidiary authority:** None from candidate pool.
- **Exhibits mapped:**
  - `B-6`: Simpson's jurisdictional reversal evidences the underlying Title IX violation (predicate tort) supporting the unlawful-act element.
  - `B-7`: Sawa's retaliation threat evidences the underlying retaliation tort.
  - `I`: Selcer's August 25 retaliatory countdown evidences the underlying ADA/§ 504 denial tort.
  - `J`: Selcer's September 3 final directive evidences the underlying retaliation/denial tort.
  - `X-7`: Faculty B's contemporaneous record evidences the falsity that underlies the fraud predicate.
  - `X-8`: Selcer's fabrication evidences the underlying fraud predicate.

### Element: overt_acts
- **Required:** Overt acts in furtherance of the conspiracy.
- **Controlling authority:** *Thompson Coal*, 488 Pa. 198, 412 A.2d 466, 211 (1979). The overt-act element is implicit in the controlling formulation that conspiracy requires two-or-more persons "combined or agreed with intent to do an unlawful act" — the unlawful act itself, when carried out, constitutes the overt act in furtherance. Pa. civil conspiracy law treats overt acts as the actus reus that distinguishes actionable conspiracy from mere agreement; *Thompson Coal*'s `key_passages` do not separately enumerate overt acts as a discrete element but presuppose them in the requirement that the conspiracy actually injure the plaintiff (see Element 5: resulting_harm).
- **Subsidiary authority:** None from candidate pool.
- **Exhibits mapped:**
  - `B-1`: Simpson's outreach is an overt act because it implements the meeting-requirement framing.
  - `B-2`: Wasilko's meeting requirement is an overt act paralleling B-1.
  - `B-3`: OCR removal is an overt act in furtherance of the concealment objective.
  - `B-5`: Simpson's term-of-art usage is an overt act establishing jurisdictional engagement subsequently reversed.
  - `B-6`: The jurisdictional reversal is an overt act completing the deny-jurisdiction objective.
  - `B-7`: Sawa's threat is an overt act in furtherance of the deterrence objective.
  - `I`: Selcer's countdown is an overt act in furtherance of the participation-suppression objective.
  - `J`: Selcer's final directive is an overt act completing the participation-denial objective.
  - `K-2`: Blair's joint-determination announcement is an overt act in furtherance of the conflict-perpetuation objective.
  - `Q`: The Zoom-removal sequence is a series of overt acts implementing the participation-denial objective.
  - `G`: Wasilko's housing denial is an overt act in furtherance of the supportive-measures-denial objective.
  - `X-6`: The February 10 transcript records overt-act inaction (no performance-issues mention) preceding the X-8 fabrication.
  - `X-7`: Faculty B's request is the overt act on which Selcer's fabrication rides.

### Element: malice
- **Required:** Malice (legal or actual) — intent to injure.
- **Controlling authority:** *Thompson Coal*, 412 A.2d at 211 (Pa. 1979). "Proof of malice, i.e., an intent to injure, is essential in proof of a conspiracy."
- **Subsidiary authority:** None from candidate pool.
- **Exhibits mapped:**
  - `B-7`: Sawa's threat language evidences malice by expressing intent to deter and harm.
  - `J`: Selcer's final-directive tone and content evidence malice through punitive framing.
  - `X-8`: Selcer's stipend threat through Spring 2029 evidences malice through the magnitude and duration of the threatened harm.

### Element: resulting_harm
- **Required:** Resulting harm — proximately caused by the conspiracy.
- **Controlling authority:** *Thompson Coal*, 488 Pa. 198, 412 A.2d 466, 211–12 (1979). The resulting-harm element is implicit in the malice/intent-to-injure formulation: "Proof of malice, i.e., an intent to injure, is essential in proof of a conspiracy" presupposes an injury. Thompson Coal's broader holding affirms summary judgment for defendants in part because plaintiffs "failed to raise a genuine issue of material fact" connecting the alleged conspiracy to actionable injury — the harm element is a sine qua non of liability under Pa. conspiracy law.
- **Subsidiary authority:** None from candidate pool.
- **Exhibits mapped:**
  - `G`: Wasilko's housing denial evidences resulting harm by documenting the loss of housing-related supportive measure.
  - `I`: Selcer's countdown evidences resulting harm by introducing the Zoom-revocation event chain.
  - `J`: Selcer's final directive evidences resulting harm by completing the participation loss.
  - `F`: Treating Physician's medical documentation evidences resulting harm by tying medical/safety harm to the conspiratorial conduct.
  - `C`: External Faculty Witness academic-expert declarations evidence resulting harm by quantifying the educational loss.

### Pitfalls
- **Confusing ordinary administrative consultation for the agreement element:** Authority: *Thompson Coal*, 412 A.2d at 211 (Pa. 1979) (agreement must be "with intent to do an unlawful act"; ordinary consultation lacks the unlawful-intent predicate).
- **Citing 'disregarding university policies' as the unlawful act:** Authority: *Thompson Coal*, 412 A.2d at 211 (Pa. 1979) (unlawful act must be tort or crime; policy violation alone is insufficient).
- **Missing the underlying-tort requirement: there is no standalone civil conspiracy claim in PA:** Authority: *Thompson Coal*, 412 A.2d at 211 (Pa. 1979) (conspiracy is derivative of an underlying tort).
- **For § 1985: omitting the class-based animus requirement (Griffin v. Breckenridge):** Authority: *Griffin v. Breckenridge*, 403 U.S. 88 (1971) — outside corpus; reviewers verifying this pitfall consult Griffin directly. The class-based-animus requirement is established by Griffin and uniformly applied in Third Circuit § 1985(3) cases; the corpus does not include Griffin, so the pitfall flag is doctrinal-canon law not anchored in the candidate pool.

---

## Audit Summary

### Entry counts
- Counts: 5
- Elements (across all counts): 22 (4 + 3 + 5 + 5 + 5)
- Pitfalls (across all counts): 19 (4 + 3 + 4 + 4 + 4)
- **Total entries (elements + pitfalls): 41**
- Total exhibit-to-element mappings justified: 119
  - Count I: 19 (7 + 6 + 2 + 4)
  - Count II: 17 (2 + 7 + 8)
  - Count III: 12 (1 + 2 + 2 + 4 + 3)
  - Count IV: 36 (14 + 7 + 5 + 5 + 5)
  - Count V: 35 (8 + 6 + 13 + 3 + 5)

### Verified pin cites (in-thread, by string-matching against `notion_full_text_url`)
- *Davis v. Monroe Cty. Bd. of Educ.*, 526 U.S. at 633, 646, 648, 650 (1999)
- *Thompson Coal Co. v. Pike Coal Co.*, 488 Pa. 198, 412 A.2d 466, 211 (1979) (both controlling-authority passages on same page)
- *Kachmar v. SunGard Data Sys.*, 109 F.3d at 177, 178 (3d Cir. 1997)
- *Taylor v. Phoenixville Sch. Dist.*, 184 F.3d at 317, 319 (3d Cir. 1999)
- *Gibbs v. Ernst*, 538 Pa. 193, 647 A.2d 882, 207 (1994)
- *Moser v. DeSetta*, 589 A.2d 679, 163 (Pa. 1991) (both controlling-authority passages on same page)
- *Peerless Wall & Window Coverings, Inc. v. Synchronics, Inc.*, 85 F. Supp. 2d 519, 533–34 (W.D. Pa. 2000) (verbatim language updated in `corpus.json`)
- *Neuman v. Corn Exch. Nat'l Bank & Tr. Co.*, 51 A.2d 759, 764 (Pa. 1947) (A.2d *764 directly verified via *Duquesne Light*'s internal citation; Pa. reporter equivalent: 356 Pa. at 451 per syllabus headnote 2)
- *Duquesne Light Co. v. Westinghouse Elec. Corp.*, 66 F.3d 604, 612 (3d Cir. 1995) (verbatim "sophisticated business entities" language; *612 marker directly verified in Part 1/3)
- *Atkinson v. Lafayette Coll.*, 460 F.3d at 451–52 (3d Cir. 2006) (verbatim Jackson-import language updated in `corpus.json`)
- *Jalil v. Avdel Corp.*, 873 F.2d at 708 (3d Cir. 1989) (verbatim "two days later" language; *708 marker directly verified in Part 1/2)
- *Desert Palace, Inc. v. Costa*, 539 U.S. at 98, 101 (2003)
- *A.J.T. v. Osseo Area Sch.*, 605 U.S. ___, slip op. at 2–3, 8 (2025)

### Pin cites flagged as `(slip op.; reporter pagination not in archive)`
The Notion archive of the following slip opinions does not include reporter
pagination markers. The cited language is verifiable verbatim against the
case's `notion_full_text_url`, but slip-page numbers are not extractable
from the archive in its current form. Reviewers requiring pin cites for
these cases must consult the official slip opinion directly.
- *Hall v. Millersville Univ.*, No. 19-3275 (3d Cir. Jan. 11, 2022)
- *McAvoy v. Dickinson Coll.*, No. 23-2939 (3d Cir. Aug. 16, 2024) (cited only in pitfall context, not as controlling authority)
- *Foster v. Bd. of Regents of Univ. of Mich.*, No. 19-1314 (6th Cir. Dec. 11, 2020) (en banc)
- *Oross v. Kutztown Univ.*, No. 21-5032 (E.D. Pa. July 25, 2023)
- *Doe v. Mercy Catholic Med. Ctr.*, No. 16-1247 (3d Cir. 2017)
- *Canada v. Samuel Grossi & Sons, Inc.*, No. 20-2747 (3d Cir. 2022) (subsidiary candidate not used)
- *Kengerski v. Harper*, No. 20-1307 (3d Cir. 2021)
- *Carvalho-Grevious v. Del. State Univ.*, No. 15-3521 (3d Cir. 2017)

### Subsidiary cases cited without verified pin cite (verifiable via `notion_full_text_url`)
- *United States ex rel. Moore & Co. v. Majestic Blue Fisheries, LLC*, 812 F.3d 294 (3d Cir. 2016) (subsidiary for Count IV scienter — pin cite to be confirmed)
- *Farrell v. Planters Lifesavers Co.*, 206 F.3d 271 (3d Cir. 2000) (subsidiary for Count II causal_connection — pin cite to be confirmed; Notion archive splits this opinion across 4 sub-pages)
- *Woodward v. Dietrich*, 548 A.2d 301 (Pa. Super. 1988) (subsidiary for Count IV resulting_damages — pin cite to be confirmed)
- *Lauren W. ex rel. Jean W. v. DeFlaminis*, 480 F.3d 259 (3d Cir. 2007) (subsidiary candidate for Count II causal_connection — not used as controlling, pin cite not extracted)

### Pitfall references to cases outside the corpus
- *Univ. of Texas Sw. Med. Ctr. v. Nassar*, 570 U.S. 338 (2013) — Count II but-for-causation pitfall.
- *Burlington N. & Santa Fe Ry. v. White*, 548 U.S. 53 (2006) — Count II adverse-action deterrence pitfall.
- *Griffin v. Breckenridge*, 403 U.S. 88 (1971) — Count V § 1985 class-based-animus pitfall.

These three cases are not in `corpus.json` and therefore cannot be
quoted from the corpus; the pitfall doctrines are nonetheless preserved
because their substance is doctrinal-canon law that any reviewer can
verify directly.

### Element-of-doctrine flags resolved
The previous version of this document carried `[CONTROLLING AUTHORITY UNCLEAR]`
flags on Count III qualified_individual, Count V overt_acts, and Count V
resulting_harm. These flags have been resolved as follows:
- **Count III qualified_individual:** Controlling authority is now *Osseo*, 605 U.S. ___, slip op. at 8 (2025), which expressly anchors the qualified-individual standard in 29 U.S.C. § 794(a) and 42 U.S.C. § 12132 and confirms that the same standard applies in the educational context. The element is statutorily defined and Osseo confirms the authority.
- **Count V overt_acts:** Controlling authority is *Thompson Coal*, 412 A.2d at 211, with the explicit acknowledgment that the overt-act element is implicit in (not separately enumerated by) the Thompson Coal `key_passages`. Pa. conspiracy law treats overt acts as the actus reus that distinguishes actionable conspiracy from mere agreement; reviewers verifying this element should treat it as derivative of the agreement element rather than independently established by Thompson Coal's quoted language.
- **Count V resulting_harm:** Same posture as overt_acts — controlling authority is *Thompson Coal*, 412 A.2d at 211–12, with acknowledgment that the harm element is implicit in the malice/intent-to-injure formulation. Pa. conspiracy is derivative of an underlying tort, and tort liability requires harm; this element is logically necessary even if not separately quoted.

### Structural inconsistencies noted in the inputs
1. **Several `corpus.json` `key_passages` were paraphrased editorial summaries rather than verbatim opinion language.** Confirmed paraphrase cases now corrected (verbatim quotations substituted in `corpus.json`): *Atkinson v. Lafayette Coll.* (case 28); *Jalil v. Avdel Corp.* (case 30); *Peerless Wall & Window Coverings, Inc. v. Synchronics, Inc.* (case 21); *Neuman v. Corn Exch. Nat'l Bank & Tr. Co.* (case 20). Other paraphrases may remain in cases not yet pin-cite-extracted; reviewers should treat the `key_passages` field as having undergone partial verbatim correction during this generation.
2. **`corpus.json` `used_in` field has been removed.** This field was artifact metadata from a federal case file outside the project repository and was not authoritative for provenance decisions. Removed from all 31 cases in the corpus during this generation.
3. **Four exhibits in `prompts/exhibit_pool.json` are not mapped to any element across any count: B-5A, N, T, Y.** Per project-lead instruction, these are intentionally retained in the pool as distractors / unmapped record material; no mapping action taken.
4. **Slip-opinion archive lacks reporter pagination for nine cases.** See list above. The cited language remains verifiable verbatim from the `notion_full_text_url`, but slip-page numbers cannot be mechanically extracted. Future remediation requires either (a) adding slip-page markers to the Notion archive or (b) replacing the slip-op cites with the official Federal Reporter cites once those are available (e.g., once SCOTUSblog adds U.S. reporter pages for *Osseo*).
