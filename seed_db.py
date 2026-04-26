"""
ShieldTB Kenya — Database Seeding Script v2.0
ml/data/seed/seed_shieldtb.py

Engineer 1 (ML Lead) — Sandra Kimiring'a

What this script does:
  1. Creates real system USERS (CHWs, nurses, county officers) who can log in
  2. Seeds facilities, conditions, symptoms lookup tables
  3. Seeds households across Nairobi informal settlements
  4. Seeds 200 clinically realistic patients with:
       - TB type assigned first (drives all symptoms)
       - Symptoms that match the TB type (not random)
       - Conditions that make clinical sense per TB type
       - Real CD4 counts (not booleans)
       - ShieldScore calculated from actual field values
       - Correct escalation levels per symptom severity
       - Lab results, treatments, visits, adherence logs
       - Postpartum alerts for pregnant women
       - ADR reports for patients on treatment

Clinical data sources used:
  - ShieldTB Clinical Reference Doc (doctors document)
  - Kenya TB/HIV coinfection: median CD4 = 124 cells/mm3 in active TB
    (PubMed SLATE trials, Kenya sites)
  - Nairobi informal settlement TB clusters: Kibera, Mathare, Mukuru,
    Korogocho, Huruma (PMC spatial epidemiology study 2024)
  - Kenya PLHIV on ART: ~89% coverage, Nairobi 165,903 PLHIV (NSDCC 2021)
  - TB type distribution: ~80% pulmonary, 20% extrapulmonary
    (higher extrapulmonary in PLHIV up to 40%)
  - Kenya TB treatment adherence: ~88% (Amref TB programme 2024)
"""

import os
import uuid
import random
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL        = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError(
        "Missing SUPABASE_URL or SUPABASE_SECRET_KEY in .env file.\n"
        "Make sure your .env file has both values set."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


#  KENYAN DEMOGRAPHIC DATA 

KENYAN_FEMALE_NAMES = [
    "Amina","Fatuma","Grace","Joyce","Mary","Wanjiru","Aisha","Pendo",
    "Zawadi","Rehema","Mercy","Faith","Sharon","Esther","Lydia",
    "Wairimu","Nyambura","Wambui","Njeri","Mumbi","Wanjiku","Muthoni",
    "Wacera","Wangari","Wahu","Nduta","Gaciiku","Wanjira","Njambi","Wanjiku"
]
KENYAN_MALE_NAMES = [
    "James","John","Peter","David","Samuel","Joseph","Daniel","Patrick",
    "Kevin","Brian","Eric","Moses","Elijah","Isaac","Emmanuel",
    "Kamau","Mwangi","Njoroge","Kariuki","Githinji","Mugo","Njenga",
    "Macharia","Gatheru","Gacheru","Kibe","Mbugua","Maina","Njuguna","Gichuki"
]
KENYAN_LAST_NAMES = [
    "Kamau","Odhiambo","Mwangi","Otieno","Njoroge","Kipchoge","Mutua",
    "Wambua","Githinji","Kariuki","Omondi","Achieng","Owino","Wekesa",
    "Simiyu","Barasa","Koech","Chebet","Rotich","Kiptoo","Sang",
    "Abdi","Hassan","Omar","Juma","Mwenda","Nyambura","Wairimu",
    "Kimiri","Mukuru","Njuguna","Gichuki","Waweru","Ndungu","Karanja"
]

# Real Nairobi ward GPS centroids — confirmed high TB burden
# Source: PMC spatial epidemiology study, Nairobi County 2024
NAIROBI_WARDS = {
    "Mathare":           {"lat": -1.2578, "lon": 36.8606},
    "Korogocho":         {"lat": -1.2494, "lon": 36.8876},
    "Huruma":            {"lat": -1.2611, "lon": 36.8672},
    "Kariobangi":        {"lat": -1.2558, "lon": 36.8801},
    "Dandora":           {"lat": -1.2453, "lon": 36.8934},
    "Mukuru kwa Njenga": {"lat": -1.3133, "lon": 36.8601},
    "Mukuru kwa Reuben": {"lat": -1.3089, "lon": 36.8534},
    "Kibera":            {"lat": -1.3133, "lon": 36.7847},
    "Kawangware":        {"lat": -1.2833, "lon": 36.7439},
    "Kangemi":           {"lat": -1.2617, "lon": 36.7283},
}

# TB TYPE CLINICAL LOGIC 
# symptoms drive escalation — 

TB_TYPES = {
    "pulmonary": {
        "display":            "Pulmonary TB",
        "prevalence":         0.52,
        "required_symptoms":  ["cough","fever","night_sweats","weight_loss"],
        "possible_symptoms":  ["chest_pain","breathlessness","fatigue","haemoptysis"],
        "emergency_symptoms": ["haemoptysis"],
        "urgent_symptoms":    ["breathlessness","chest_pain"],
        "common_conditions":  ["HIV","diabetes"],
        "escalation_default": "dispensary_3_days",
    },
    "tb_lymphadenitis": {
        "display":            "TB Lymphadenitis",
        "prevalence":         0.08,
        "required_symptoms":  ["swollen_lymph_nodes","fever","fatigue"],
        "possible_symptoms":  ["night_sweats","weight_loss","neck_stiffness"],
        "emergency_symptoms": [],
        "urgent_symptoms":    ["swollen_lymph_nodes"],
        "common_conditions":  ["HIV","pregnancy"],
        "escalation_default": "dispensary_3_days",
    },
    "skeletal_tb": {
        "display":            "Skeletal TB (Pott's Disease)",
        "prevalence":         0.04,
        "required_symptoms":  ["back_pain","fatigue"],
        "possible_symptoms":  ["leg_weakness","weight_loss","fever"],
        "emergency_symptoms": ["leg_weakness"],
        "urgent_symptoms":    ["back_pain","leg_weakness"],
        "common_conditions":  ["HIV","diabetes","CKD"],
        "escalation_default": "urgent_same_day",
    },
    "miliary_tb": {
        "display":            "Miliary TB",
        "prevalence":         0.05,
        "required_symptoms":  ["fever","breathlessness","fatigue","weight_loss"],
        "possible_symptoms":  ["abdominal_pain","headache","night_sweats"],
        "emergency_symptoms": ["breathlessness","headache"],
        "urgent_symptoms":    ["fever","breathlessness"],
        "common_conditions":  ["HIV"],
        "escalation_default": "emergency_999",
        "cd4_max":            150,
    },
    "tb_meningitis": {
        "display":            "TB Meningitis",
        "prevalence":         0.04,
        "required_symptoms":  ["headache","neck_stiffness","fever"],
        "possible_symptoms":  ["fatigue","weight_loss"],
        "emergency_symptoms": ["headache","neck_stiffness"],
        "urgent_symptoms":    [],
        "common_conditions":  ["HIV"],
        "escalation_default": "emergency_999",
        "cd4_max":            200,
    },
    "abdominal_tb": {
        "display":            "Abdominal TB",
        "prevalence":         0.05,
        "required_symptoms":  ["abdominal_pain","weight_loss","fever"],
        "possible_symptoms":  ["fatigue","night_sweats","breathlessness"],
        "emergency_symptoms": [],
        "urgent_symptoms":    ["abdominal_pain"],
        "common_conditions":  ["HIV","diabetes"],
        "escalation_default": "dispensary_3_days",
    },
    "pleural_tb": {
        "display":            "Pleural TB",
        "prevalence":         0.06,
        "required_symptoms":  ["chest_pain","breathlessness","fever"],
        "possible_symptoms":  ["cough","night_sweats","fatigue","weight_loss"],
        "emergency_symptoms": ["breathlessness"],
        "urgent_symptoms":    ["chest_pain","breathlessness"],
        "common_conditions":  ["HIV","SLE"],
        "escalation_default": "urgent_same_day",
    },
    "pericardial_tb": {
        "display":            "Pericardial TB",
        "prevalence":         0.03,
        "required_symptoms":  ["chest_pain","breathlessness","fatigue"],
        "possible_symptoms":  ["fever","night_sweats","weight_loss","leg_weakness"],
        "emergency_symptoms": ["chest_pain","breathlessness"],
        "urgent_symptoms":    ["chest_pain"],
        "common_conditions":  ["HIV","SLE"],
        "escalation_default": "urgent_same_day",
    },
    "renal_tb": {
        "display":            "Renal/Urogenital TB",
        "prevalence":         0.04,
        "required_symptoms":  ["blood_in_urine","fatigue"],
        "possible_symptoms":  ["fever","weight_loss","abdominal_pain","night_sweats"],
        "emergency_symptoms": [],
        "urgent_symptoms":    ["blood_in_urine"],
        "common_conditions":  ["HIV","CKD","diabetes"],
        "escalation_default": "dispensary_3_days",
    },
    "cutaneous_tb": {
        "display":            "Cutaneous TB",
        "prevalence":         0.03,
        "required_symptoms":  ["skin_lesion","fatigue"],
        "possible_symptoms":  ["fever","weight_loss","swollen_lymph_nodes"],
        "emergency_symptoms": [],
        "urgent_symptoms":    ["skin_lesion"],
        "common_conditions":  ["HIV","SLE","TNF_inhibitor_use"],
        "escalation_default": "dispensary_3_days",
    },
    "ltbi": {
        "display":            "Latent TB (LTBI) — no symptoms",
        "prevalence":         0.06,
        "required_symptoms":  [],
        "possible_symptoms":  [],
        "emergency_symptoms": [],
        "urgent_symptoms":    [],
        "common_conditions":  ["HIV","pregnancy","diabetes","SLE"],
        "escalation_default": "monitor_chatbot",
    },
}

CONDITIONS_LIST = [
    "HIV","pregnancy","SLE","diabetes",
    "CKD","TNF_inhibitor_use",
    "haematological_malignancy","organ_transplant"
]

# ART regimens used in Kenya (MOH 2022 guidelines)
ART_REGIMENS = [
    "TDF/3TC/DTG",    # First-line preferred
    "TDF/3TC/EFV",    # First-line alternative
    "AZT/3TC/NVP",    # Second-line
    "TDF/3TC/LPV/r",  # Second-line
    "ABC/3TC/DTG",    # Alternative
]

# ShieldScore weights — from Clinical Reference Doc
SCORE_WEIGHTS = {
    "HIV":                       22,
    "cd4_below_200":             18,
    "household_contact":         15,
    "haematological_malignancy": 15,
    "organ_transplant":          15,
    "pregnancy":                 12,
    "SLE":                       10,
    "TNF_inhibitor_use":         10,
    "CKD":                        8,
    "diabetes":                   7,
}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def uid():
    return str(uuid.uuid4())

def days_ago(n):
    return (datetime.now() - timedelta(days=n)).isoformat()

def date_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()

def gps_near(lat, lon, r=0.006):
    return (
        round(lat + random.uniform(-r, r), 6),
        round(lon + random.uniform(-r, r), 6),
    )

def kenyan_phone():
    prefixes = [
        "0700","0701","0710","0711","0720","0721","0722","0723",
        "0724","0725","0726","0727","0728","0729","0740","0741",
        "0745","0757","0758","0768","0790","0791","0793","0794",
        "0795","0796","0797","0798","0799"
    ]
    return random.choice(prefixes) + str(random.randint(100000, 999999))

def kenyan_name(sex):
    first = random.choice(KENYAN_FEMALE_NAMES if sex == "F" else KENYAN_MALE_NAMES)
    return f"{first} {random.choice(KENYAN_LAST_NAMES)}"

def pick_tb_type():
    types   = list(TB_TYPES.keys())
    weights = [TB_TYPES[t]["prevalence"] for t in types]
    return random.choices(types, weights=weights, k=1)[0]

def escalation_level(tb_key, symptoms):
    tb   = TB_TYPES[tb_key]
    syms = set(symptoms)
    if any(s in syms for s in tb["emergency_symptoms"]):
        return "emergency_999"
    if any(s in syms for s in tb["urgent_symptoms"]):
        return "urgent_same_day"
    return tb["escalation_default"]

def shield_score(conditions, cd4, household_contact, symptom_count):
    score = sum(SCORE_WEIGHTS.get(c, 0) for c in conditions)
    if "HIV" in conditions and cd4 is not None and cd4 < 200:
        score += SCORE_WEIGHTS["cd4_below_200"]
    if household_contact:
        score += SCORE_WEIGHTS["household_contact"]
    score += min(symptom_count * 3, 15)
    if score >= 61: return score, "critical"
    if score >= 41: return score, "high"
    if score >= 21: return score, "medium"
    return score, "low"

def cd4_for_patient(conditions, tb_key):
    """Real CD4 integer. Median 124 in active TB/HIV Kenya (SLATE trial)."""
    if "HIV" not in conditions:
        return None
    cd4_max = TB_TYPES[tb_key].get("cd4_max", None)
    if cd4_max:
        return random.randint(20, cd4_max)
    if tb_key in ("pulmonary","abdominal_tb","pleural_tb"):
        return random.randint(50, 350)
    return random.randint(100, 800)


# ─── SEED FUNCTIONS ───────────────────────────────────────────────────────────

def seed_facilities():
    print("\n Seeding facilities...")
    rows = [
        {"name":"Mathare North Health Centre",    "sub":"Mathare",       "ward":"Mathare"},
        {"name":"Korogocho Dispensary",           "sub":"Korogocho",     "ward":"Korogocho"},
        {"name":"Huruma Sub-District Hospital",   "sub":"Huruma",        "ward":"Huruma"},
        {"name":"Kariobangi Health Centre",       "sub":"Kariobangi",    "ward":"Kariobangi"},
        {"name":"Dandora Phase 2 Dispensary",     "sub":"Dandora",       "ward":"Dandora"},
        {"name":"Mukuru Kwa Njenga Dispensary",   "sub":"Embakasi East", "ward":"Mukuru kwa Njenga"},
        {"name":"Mukuru Kwa Reuben Dispensary",   "sub":"Embakasi East", "ward":"Mukuru kwa Reuben"},
        {"name":"Kibera South Health Centre",     "sub":"Langata",       "ward":"Kibera"},
        {"name":"Kangemi Health Centre",          "sub":"Westlands",     "ward":"Kangemi"},
        {"name":"Kenyatta National Hospital OPD", "sub":"Starehe",       "ward":"Mathare"},
    ]
    ids = {}
    for r in rows:
        fid = uid()
        w   = NAIROBI_WARDS.get(r["ward"], {"lat":-1.2921,"lon":36.8219})
        lat, lon = gps_near(w["lat"], w["lon"], 0.002)
        supabase.table("facilities").insert({
            "id":uid(), "name":r["name"], "county":"Nairobi",
            "subcounty":r["sub"], "lat":lat, "long":lon,
            "created_at":days_ago(random.randint(60,365)),
        }).execute()
        # re-fetch to get actual id we just used
        ids[r["name"]] = fid
    # Simpler: just insert and track
    ids = {}
    res = supabase.table("facilities").select("id,name").execute()
    for row in res.data:
        ids[row["name"]] = row["id"]
    print(f"   ✓ {len(ids)} facilities")
    return ids


def seed_lookups():
    print(" Seeding conditions & symptoms...")
    cond_ids = {}
    for name in CONDITIONS_LIST:
        cid = uid()
        supabase.table("conditions").insert({"id":cid,"name":name}).execute()
        cond_ids[name] = cid

    all_syms = set()
    for tb in TB_TYPES.values():
        all_syms.update(tb["required_symptoms"])
        all_syms.update(tb["possible_symptoms"])
    sym_ids = {}
    for name in all_syms:
        sid = uid()
        supabase.table("symptoms").insert({"id":sid,"name":name}).execute()
        sym_ids[name] = sid

    print(f"   ✓ {len(cond_ids)} conditions, {len(sym_ids)} symptoms")
    return cond_ids, sym_ids


def seed_users(fac_ids):
    """
    The REAL system users — people who log into the app.
    Named Kenyan health workers with realistic roles and facilities.
    """
    print("Seeding system users...")

    fac_list = list(fac_ids.values())

    staff = [
        {"name":"Grace Wanjiru Kamau",        "role":"chw",           "fac":"Mathare North Health Centre",    "email":"grace.kamau@shieldtb.ke"},
        {"name":"Peter Odhiambo Otieno",       "role":"chw",           "fac":"Korogocho Dispensary",           "email":"peter.otieno@shieldtb.ke"},
        {"name":"Mercy Njoroge Mwangi",        "role":"chw",           "fac":"Huruma Sub-District Hospital",   "email":"mercy.mwangi@shieldtb.ke"},
        {"name":"Samuel Kipchoge Mutua",       "role":"chw",           "fac":"Kariobangi Health Centre",       "email":"samuel.mutua@shieldtb.ke"},
        {"name":"Aisha Abdi Hassan",           "role":"chw",           "fac":"Dandora Phase 2 Dispensary",     "email":"aisha.hassan@shieldtb.ke"},
        {"name":"Joyce Wambua Githinji",       "role":"chw",           "fac":"Mukuru Kwa Njenga Dispensary",   "email":"joyce.githinji@shieldtb.ke"},
        {"name":"David Kariuki Njoroge",       "role":"chw",           "fac":"Mukuru Kwa Reuben Dispensary",   "email":"david.njoroge@shieldtb.ke"},
        {"name":"Fatuma Omar Juma",            "role":"chw",           "fac":"Kibera South Health Centre",     "email":"fatuma.juma@shieldtb.ke"},
        {"name":"Brian Wekesa Simiyu",         "role":"chw",           "fac":"Kangemi Health Centre",          "email":"brian.simiyu@shieldtb.ke"},
        {"name":"Rehema Barasa Koech",         "role":"chw",           "fac":"Mathare North Health Centre",    "email":"rehema.koech@shieldtb.ke"},
        {"name":" Mary Muthoni Kariuki",       "role":"nurse",         "fac":"Huruma Sub-District Hospital",   "email":"mary.kariuki@shieldtb.ke"},
        {"name":" Esther Chebet Sang",         "role":"nurse",         "fac":"Mathare North Health Centre",    "email":"esther.sang@shieldtb.ke"},
        {"name":" Lydia Rotich Kiptoo",        "role":"nurse",         "fac":"Kibera South Health Centre",     "email":"lydia.kiptoo@shieldtb.ke"},
        {"name":" Isaac Omondi Owino",         "role":"nurse",         "fac":"Mukuru Kwa Njenga Dispensary",   "email":"isaac.owino@shieldtb.ke"},
        {"name":" Zawadi Achieng",             "role":"nurse",         "fac":"Korogocho Dispensary",           "email":"zawadi.achieng@shieldtb.ke"},
        {"name":" Emmanuel Githinji",          "role":"nurse",         "fac":"Kenyatta National Hospital OPD", "email":"emmanuel.githinji@shieldtb.ke"},
        {"name":"Dr. James Kamau Njuguna",     "role":"admin","fac":"Kenyatta National Hospital OPD", "email":"james.njuguna@shieldtb.ke"},
        {"name":"Dr. Pendo Mwenda Waweru",     "role":"admin","fac":"Kenyatta National Hospital OPD", "email":"pendo.waweru@shieldtb.ke"},
    ]


    chw_ids = []
    for s in staff:
        fid = fac_ids.get(s["fac"], random.choice(fac_list))

        # create auth user first, then profile uses that same id
        auth_response = supabase.auth.admin.create_user({
            "email":          s["email"],
            "password":       "ShieldTB@2025",
            "email_confirm":  True,
            "user_metadata":  {"full_name": s["name"], "role": s["role"]},
        })
        user_id = auth_response.user.id

        supabase.table("profiles").insert({
            "id":          user_id,
            "full_name":   s["name"],
            "role":        s["role"],
            "facility_id": fid,
            "created_at":  days_ago(random.randint(14, 180)),
        }).execute()

        if s["role"] == "chw":
            chw_ids.append(user_id)

    print(f"    {len(staff)} users (10 CHWs, 6 nurses, 2 admins)")
    return chw_ids


def seed_households():
    print("Seeding households...")
    hh_list = []
    for _ in range(70):
        hid  = uid()
        ward = random.choice(list(NAIROBI_WARDS.keys()))
        w    = NAIROBI_WARDS[ward]
        lat, lon = gps_near(w["lat"], w["lon"])
        size = random.choices(
            [3,4,5,6,7,8,9,10,12,15,20],
            weights=[5,8,12,14,14,12,10,8,6,5,6], k=1
        )[0]
        supabase.table("households").insert({
            "id":hid, "gps_lat":lat, "gps_long":lon,
            "address_desc":f"{ward}, Nairobi — Plot {random.randint(1,999)}",
            "household_size":size,
            "created_at":days_ago(random.randint(10,200)),
        }).execute()
        hh_list.append({"id":hid,"ward":ward,"size":size})
    print(f"   ✓ {len(hh_list)} households")
    return hh_list


def seed_patients(hh_list, fac_ids, chw_ids, cond_ids, sym_ids):
    print("  Seeding 200 patients...")
    fac_list = list(fac_ids.values())
    dist     = {"low":0,"medium":0,"high":0,"critical":0}

    for i in range(200):
        sex     = random.choice(["M","F"])
        hh      = random.choice(hh_list)
        fac_id  = random.choice(fac_list)
        chw_id  = random.choice(chw_ids) if chw_ids else None
        tb_key  = pick_tb_type()
        tb      = TB_TYPES[tb_key]

        
        phone = kenyan_phone()
        temp_id = uid()
        auth_response = supabase.auth.admin.create_user({
            "email":         f"patient.{temp_id[:8]}@shieldtb.ke",
            "password":      "ShieldTB@2025",
            "email_confirm": True,
        })
        pid = auth_response.user.id

        # patients need a profile row too (foreign key requirement)
        supabase.table("profiles").insert({
            "id":          pid,
            "full_name":   kenyan_name(sex),
            "role":        "patient",
            "facility_id": random.choice(fac_list),
            "created_at":  days_ago(random.randint(1, 300)),
        }).execute()

        supabase.table("patients").insert({
            "id":pid, "phone":phone,
            "created_at":days_ago(random.randint(1,300)),
        }).execute()

        # Household membership
        is_index = (tb_key != "ltbi") and (random.random() < 0.20)
        supabase.table("household_members").insert({
            "id":uid(), "household_id":hh["id"], "patient_id":pid,
            "relationship":random.choice(["spouse","child","parent","sibling","grandparent","tenant","other"]),
            "is_index_case":is_index,
        }).execute()

        # Conditions — guided by TB type
        conditions = []
        if tb_key in ("miliary_tb","tb_meningitis"):
            conditions = ["HIV"]  
        else:
            for c in tb["common_conditions"]:
                if c == "pregnancy" and sex == "M":
                    continue
                if random.random() < (0.70 if c == "HIV" else 0.45):
                    conditions.append(c)
            if random.random() < 0.25:
                extras = [c for c in CONDITIONS_LIST if c not in conditions and not (c == "pregnancy" and sex == "M")]
                if extras:
                    conditions.append(random.choice(extras))

        for c in conditions:
            supabase.table("patient_conditions").insert({
                "id":uid(), "patient_id":pid,
                "condition_id":cond_ids[c],
                "status":"active",
                "recorded_at":days_ago(random.randint(1,120)),
            }).execute()

        # CD4 count — real integer
        cd4 = cd4_for_patient(conditions, tb_key)
        art = random.choice(ART_REGIMENS) if "HIV" in conditions else None

        # Symptoms — driven by TB type, not random
        syms = list(tb["required_symptoms"])
        for s in tb["possible_symptoms"]:
            if random.random() < 0.55:
                syms.append(s)

        for s in syms:
            if s in sym_ids:
                supabase.table("patient_symptoms").insert({
                    "id":uid(), "patient_id":pid, "symptom_id":sym_ids[s],
                    "severity":random.randint(2,5),
                    "duration_days":random.randint(7,90),
                    "recorded_at":days_ago(random.randint(1,30)),
                }).execute()

        # ShieldScore
        hh_contact       = is_index or (random.random() < 0.40)
        score_val, level = shield_score(conditions, cd4, hh_contact, len(syms))
        dist[level]     += 1

        supabase.table("risk_scores").insert({
            "id":uid(), "patient_id":pid,
            "risk_level":level,
            "score":round(min(score_val,100)/100, 4),
            "model_version":"rule_based_v1",
            "created_at":days_ago(random.randint(0,30)),
        }).execute()

        # Alerts
        esc = escalation_level(tb_key, syms)
        if level in ("high","critical") or esc in ("urgent_same_day","emergency_999"):
            alert_id = uid()
            supabase.table("alerts").insert({
                "id":alert_id, "patient_id":pid, "household_id":hh["id"],
                "alert_type":f"{level}_risk_{esc}",
                "status":random.choice(["pending","acknowledged","resolved"]),
                "created_at":days_ago(random.randint(0,14)),
            }).execute()
            if level in ("high","critical") and chw_id:
                supabase.table("chw_tasks").insert({
                    "id":uid(), "chw_id":chw_id, "alert_id":alert_id,
                    "description":f"Visit household. {tb['display']}. Risk: {level}. Escalation: {esc}.",
                    "due_date":days_ago(-random.randint(1,5)),
                    "status":random.choice(["pending","in_progress"]),
                }).execute()

        # Lab results
        if tb_key in ("pulmonary","miliary_tb","pleural_tb"):
            supabase.table("lab_results").insert({
                "id":uid(), "patient_id":pid, "test_type":"GeneXpert_MTB_RIF",
                "result":random.choices(
                    ["MTB detected RIF sensitive","MTB detected RIF resistant","MTB not detected","Invalid"],
                    weights=[45,8,42,5],k=1
                )[0],
                "result_date":date_ago(random.randint(1,45)),
                "facility_id":fac_id,
            }).execute()

        if "HIV" in conditions and cd4 is not None:
            supabase.table("lab_results").insert({
                "id":uid(), "patient_id":pid, "test_type":"CD4_count",
                "result":f"{cd4} cells/mm3",
                "result_date":date_ago(random.randint(7,90)),
                "facility_id":fac_id,
            }).execute()

        # Treatments + adherence logs
        if level in ("high","critical") and random.random() < 0.75:
            tx_type = random.choices(
                ["3HP_TPT","6H_isoniazid_TPT","2HRZE_4HR_first_line","MDR_TB_regimen"],
                weights=[30,25,35,10],k=1
            )[0]
            supabase.table("treatments").insert({
                "id":uid(), "patient_id":pid,
                "treatment_type":tx_type,
                "start_date":date_ago(random.randint(1,60)),
                "end_date":None,
            }).execute()
            # Adherence logs — 88% adherence rate (Kenya Amref programme)
            for day in range(random.randint(7,45), 0, -1):
                supabase.table("adherence_logs").insert({
                    "id":uid(), "patient_id":pid,
                    "date":date_ago(day),
                    "status":random.choices(["taken","missed"],weights=[88,12],k=1)[0],
                }).execute()

        # Visits
        for _ in range(random.randint(1,4)):
            supabase.table("visits").insert({
                "id":uid(), "patient_id":pid, "chw_id":chw_id,
                "visit_type":random.choice([
                    "initial_screening","follow_up",
                    "tpt_review","adr_check","postpartum_check"
                ]),
                "visit_date":days_ago(random.randint(0,120)),
                "notes":(
                    f"TB: {tb['display']} | Score: {score_val} | "
                    f"Risk: {level} | Escalation: {esc} | "
                    f"CD4: {cd4 or 'N/A'} | ART: {art or 'N/A'}"
                ),
            }).execute()

        # Screenings
        screen = (
            "emergency_referral" if esc == "emergency_999" else
            "urgent_referral"    if esc == "urgent_same_day" else
            "presumptive_tb"     if level in ("high","critical") else
            "ltbi_suspected"     if tb_key == "ltbi" else
            "negative"
        )
        supabase.table("screenings").insert({
            "id":uid(), "patient_id":pid, "chw_id":chw_id,
            "screening_result":screen,
            "notes":f"WHO 4-symptom. {tb['display']}. Conditions: {', '.join(conditions) or 'none'}.",
            "created_at":days_ago(random.randint(1,60)),
        }).execute()

        # ADR reports
        if art and random.random() < 0.15:
            supabase.table("adr_reports").insert({
                "id":uid(), "patient_id":pid,
                "symptom":random.choice([
                    "nausea and vomiting","peripheral neuropathy",
                    "skin rash","jaundice","dizziness"
                ]),
                "severity":random.choice(["mild","moderate","severe"]),
                "reported_at":days_ago(random.randint(1,30)),
            }).execute()

        # Postpartum alerts for pregnant women
        if "pregnancy" in conditions and sex == "F":
            delivery_days = random.randint(1,90)
            for check_day in [30,60,90]:
                if delivery_days >= check_day:
                    supabase.table("alerts").insert({
                        "id":uid(), "patient_id":pid, "household_id":hh["id"],
                        "alert_type":f"postpartum_day_{check_day}_check",
                        "status":"resolved" if delivery_days > check_day + 7 else "pending",
                        "created_at":days_ago(delivery_days - check_day + 1),
                    }).execute()

        if (i + 1) % 50 == 0:
            print(f"   ... {i+1}/200 patients done")

    print(f"   ✓ 200 patients seeded")
    print(f"    Risk distribution → {dist}")


def seed_hotspots():
    print("  Seeding hotspots...")
    # High-burden wards confirmed by PMC spatial epidemiology study Nairobi 2024
    clusters = [
        ("Kibera",            "critical", 28),
        ("Mukuru kwa Njenga", "critical", 24),
        ("Mathare",           "high",     19),
        ("Korogocho",         "high",     16),
        ("Huruma",            "high",     13),
        ("Mukuru kwa Reuben", "medium", 11),
        ("Dandora",           "medium",  9),
    ]
    for ward, risk, size in clusters:
        w = NAIROBI_WARDS[ward]
        lat, lon = gps_near(w["lat"], w["lon"], 0.004)
        supabase.table("hotspots").insert({
            "id":uid(), "lat":lat, "long":lon,
            "cluster_size":size + random.randint(-2,2),
            "risk_level":risk,
            "detected_at":days_ago(random.randint(1,30)),
        }).execute()
    print(f"   ✓ {len(clusters)} hotspots seeded")

def clear_tables():
    print("Clearing existing data...")
    tables = [
        "adherence_logs", "adr_reports", "chw_tasks", "alerts",
        "screenings", "visits", "treatments", "lab_results",
        "patient_symptoms", "patient_conditions", "risk_scores",
        "household_members", "hotspots", "patients", "households",
        "profiles", "symptoms", "conditions", "facilities",
    ]
    for table in tables:
        supabase.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"  cleared {table}")

    # this must be OUTSIDE the loop, indented at same level as the for
    print("  clearing auth users...")
    existing = supabase.auth.admin.list_users()
    for user in existing:
        supabase.auth.admin.delete_user(user.id)

    print("Done. Starting fresh...\n")

# main

def main():
    print("\n" + "="*60)
    print("  ShieldTB Kenya — Database Seeding Script v2.0")
    print("  ml/data/seed/seed_shieldtb.py")
    print("="*60)

    try:
        clear_tables()
        fac_ids          = seed_facilities()
        cond_ids, sym_ids = seed_lookups()
        chw_ids          = seed_users(fac_ids)
        hh_list          = seed_households()
        seed_patients(hh_list, fac_ids, chw_ids, cond_ids, sym_ids)
        seed_hotspots()

        print("\n" + "="*60)
        print("  DONE! Check Supabase Table Editor:")
        print("  → profiles    : 18 system users (CHWs, nurses, officers)")
        print("  → patients    : 200 rows")
        print("  → risk_scores : 200 rows with real ShieldScores")
        print("  → lab_results : CD4 counts + GeneXpert results")
        print("  → adherence_logs: daily medication tracking")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()