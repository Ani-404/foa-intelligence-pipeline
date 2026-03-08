import json
import os
import re


ONTOLOGY = {
    "research_domains": {
        "artificial_intelligence": {"keywords": ["artificial intelligence", "machine learning", "deep learning", "neural network", "nlp"], "definition": "AI methods and intelligent computation."},
        "health_biomedical": {"keywords": ["biomedical", "clinical", "health", "patient", "public health"], "definition": "Health and biomedical outcomes."},
        "environment_climate": {"keywords": ["climate", "environment", "sustainability", "ecology", "carbon"], "definition": "Environment and climate resilience."},
        "education_workforce": {"keywords": ["education", "training", "curriculum", "workforce", "student"], "definition": "Learning and workforce development."},
        "data_computing": {"keywords": ["data science", "analytics", "high performance computing", "cyberinfrastructure", "big data"], "definition": "Data-intensive and computing research."},
    },
    "methods_approaches": {
        "modeling_simulation": {"keywords": ["modeling", "simulation", "forecast", "predictive"], "definition": "Model-based analysis and prediction."},
        "experimental": {"keywords": ["experiment", "prototype", "pilot", "validation"], "definition": "Empirical and prototype-led approaches."},
        "survey_evaluation": {"keywords": ["survey", "evaluation", "assessment", "mixed methods"], "definition": "Survey/evaluation study designs."},
        "community_engaged": {"keywords": ["community", "participatory", "stakeholder", "co-design"], "definition": "Community and participatory methods."},
    },
    "populations": {
        "k12_students": {"keywords": ["k-12", "k12", "school students", "youth"], "definition": "K-12 learners."},
        "undergraduate_students": {"keywords": ["undergraduate", "college students"], "definition": "Undergraduate populations."},
        "graduate_postdoc": {"keywords": ["graduate", "postdoctoral", "postdoc", "doctoral"], "definition": "Graduate and postdoc populations."},
        "underserved_groups": {"keywords": ["underserved", "underrepresented", "minority-serving", "equity"], "definition": "Underserved communities."},
        "general_population": {"keywords": ["general population", "community members", "public"], "definition": "General public."},
    },
    "sponsor_themes": {
        "capacity_building": {"keywords": ["capacity building", "infrastructure", "center", "network"], "definition": "Institutional capacity building."},
        "innovation_translation": {"keywords": ["innovation", "translation", "commercialization", "technology transfer"], "definition": "Innovation and translation."},
        "interdisciplinary_collaboration": {"keywords": ["interdisciplinary", "convergence", "cross-disciplinary", "multidisciplinary"], "definition": "Cross-disciplinary collaboration."},
        "equity_inclusion": {"keywords": ["equity", "inclusion", "broadening participation", "diversity"], "definition": "Equity and inclusion priorities."},
        "evidence_based_policy": {"keywords": ["policy", "evidence-based", "implementation", "impact"], "definition": "Policy and implementation impact."},
    },
}


def _cats():
    return list(ONTOLOGY.keys())


def _empty():
    return {c: ["unspecified"] for c in _cats()}


def _text(rec):
    return " ".join([rec.get("title", ""), rec.get("eligibility", ""), rec.get("program_description", "")]).lower()


def _has(text, kw):
    return re.search(rf"\b{re.escape(kw)}\b", text, flags=re.IGNORECASE) is not None


def _rule(text):
    out = {}
    for cat, values in ONTOLOGY.items():
        tags = [tag for tag, meta in values.items() if any(_has(text, k.lower()) for k in meta["keywords"])]
        out[cat] = tags if tags else ["unspecified"]
    return out


def _merge(a, b):
    out = {}
    for cat in _cats():
        tags = sorted(set([x for x in a.get(cat, []) + b.get(cat, []) if x != "unspecified"]))
        out[cat] = tags if tags else ["unspecified"]
    return out


def _embed(text, threshold=0.33, model_name="sentence-transformers/all-MiniLM-L6-v2"):
    meta = {"embedding_model": model_name, "embedding_threshold": str(threshold)}
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception as exc:
        meta["embedding_status"] = f"unavailable: {exc.__class__.__name__}"
        return _empty(), meta

    rows = [(c, t, f"{c}: {t}. {m['definition']}") for c, vals in ONTOLOGY.items() for t, m in vals.items()]
    labels = [r[2] for r in rows]
    model = SentenceTransformer(model_name)
    sims = cosine_similarity(model.encode([text], normalize_embeddings=True), model.encode(labels, normalize_embeddings=True))[0]

    out = {c: [] for c in _cats()}
    for i, sim in enumerate(sims):
        if float(sim) >= threshold:
            out[rows[i][0]].append(rows[i][1])
    for c in out:
        out[c] = sorted(set(out[c])) if out[c] else ["unspecified"]
    meta["embedding_status"] = "enabled"
    return out, meta


def _llm(text):
    meta = {}
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        meta["llm_status"] = "skipped: missing OPENAI_API_KEY"
        return _empty(), meta
    try:
        from openai import OpenAI
    except Exception as exc:
        meta["llm_status"] = f"unavailable: {exc.__class__.__name__}"
        return _empty(), meta

    ont = {c: {t: m["definition"] for t, m in vals.items()} for c, vals in ONTOLOGY.items()}
    prompt = "Classify text into ontology tags. Return strict JSON with category keys and list values. Use only given tags or 'unspecified'.\n\n" + f"Ontology: {json.dumps(ont)}\n\nText: {text[:4000]}"
    try:
        rsp = OpenAI(api_key=api_key).responses.create(model="gpt-4.1-mini", input=prompt, temperature=0)
        data = json.loads(rsp.output_text.strip())
        out = {c: ([str(v) for v in data.get(c, ["unspecified"])] if isinstance(data.get(c, ["unspecified"]), list) else ["unspecified"]) for c in _cats()}
        meta["llm_status"] = "enabled"
        meta["llm_model"] = "gpt-4.1-mini"
        return out, meta
    except Exception as exc:
        meta["llm_status"] = f"failed: {exc.__class__.__name__}"
        return _empty(), meta


def tag_foa(foa_record, use_embeddings=False, use_llm=False):
    text = _text(foa_record)
    tags = _rule(text)
    meta = {"strategy": "rule_only", "rule_status": "enabled"}
    if use_embeddings:
        e_tags, e_meta = _embed(text)
        tags = _merge(tags, e_tags)
        meta.update(e_meta)
        meta["strategy"] = "rule_plus_embeddings"
    if use_llm:
        l_tags, l_meta = _llm(text)
        tags = _merge(tags, l_tags)
        meta.update(l_meta)
        meta["strategy"] = "rule_plus_embeddings_plus_llm" if use_embeddings else "rule_plus_llm"
    return {"tags": tags, "metadata": meta}
