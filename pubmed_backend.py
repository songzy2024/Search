#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PubMed Literature Search Web Application - Backend
Flask backend with async task processing
"""
from flask import Flask, request, jsonify, send_from_directory, make_response
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import time
import threading
import uuid
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

app = Flask(__name__, static_folder=None)

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
tasks: Dict[str, Dict[str, Any]] = {}

def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.after_request
def apply_cors(response):
    return add_cors_headers(response)

# ============================================================================
# Translation & Keyword Suggestions
# ============================================================================

MEDICAL_TERMS = {
    "糖尿病": "diabetes mellitus",
    "高血压": "hypertension",
    "冠心病": "coronary heart disease OR coronary artery disease",
    "心肌梗死": "myocardial infarction",
    "心力衰竭": "heart failure",
    "心房颤动": "atrial fibrillation",
    "脑卒中": "stroke OR cerebrovascular accident",
    "中风": "stroke",
    "阿尔茨海默病": "alzheimer disease",
    "帕金森": "parkinson disease",
    "抑郁症": "depression OR depressive disorder",
    "焦虑": "anxiety disorder",
    "精神分裂症": "schizophrenia",
    "肺癌": "lung cancer",
    "乳腺癌": "breast cancer",
    "结直肠癌": "colorectal cancer",
    "肝癌": "liver cancer OR hepatocellular carcinoma",
    "胃癌": "gastric cancer OR stomach cancer",
    "前列腺癌": "prostate cancer",
    "卵巢癌": "ovarian cancer",
    "宫颈癌": "cervical cancer",
    "白血病": "leukemia",
    "淋巴瘤": "lymphoma",
    "骨质疏松": "osteoporosis",
    "骨关节炎": "osteoarthritis",
    "类风湿性关节炎": "rheumatoid arthritis",
    "系统性红斑狼疮": "systemic lupus erythematosus",
    "慢性阻塞性肺疾病": "chronic obstructive pulmonary disease OR COPD",
    "慢性肾病": "chronic kidney disease OR CKD",
    "肝硬化": "liver cirrhosis",
    "脂肪肝": "fatty liver OR hepatic steatosis",
    "乙肝": "hepatitis B",
    "丙肝": "hepatitis C",
    "新冠肺炎": "COVID-19 OR SARS-CoV-2",
    "新冠": "COVID-19",
    "流感": "influenza",
    "肺炎": "pneumonia",
    "肺结核": "tuberculosis",
    "哮喘": "asthma",
    "银屑病": "psoriasis",
    "失眠": "insomnia",
    "肥胖": "obesity OR overweight",
    "痛风": "gout",
    "甲亢": "hyperthyroidism",
    "甲减": "hypothyroidism",
    "胰腺癌": "pancreatic cancer",
    "膀胱癌": "bladder cancer",
    "食管癌": "esophageal cancer",
    "皮肤癌": "skin cancer",
    "黑色素瘤": "melanoma",
    "脑瘤": "brain tumor OR glioma",
    "神经胶质瘤": "glioma",
    "不孕症": "infertility",
    "多囊卵巢综合征": "polycystic ovary syndrome OR PCOS",
    "先兆子痫": "preeclampsia",
    "妊娠糖尿病": "gestational diabetes",
    "败血症": "sepsis",
    "贫血": "anemia",
    "肌萎缩侧索硬化": "amyotrophic lateral sclerosis OR ALS",
    "多发性硬化": "multiple sclerosis",
    "癫痫": "epilepsy OR seizure",
    "自闭症": "autism spectrum disorder",
    "双向情感障碍": "bipolar disorder",
    "肠易激综合征": "irritable bowel syndrome OR IBS",
    "炎症性肠病": "inflammatory bowel disease OR IBD",
    "克罗恩病": "crohn disease",
    "溃疡性结肠炎": "ulcerative colitis",
    "胃炎": "gastritis",
    "胃溃疡": "gastric ulcer",
    "胃食管反流": "gastroesophageal reflux OR GERD",
    "肝炎": "hepatitis",
    "肾衰竭": "kidney failure OR renal failure",
    "肺栓塞": "pulmonary embolism",
    "深静脉血栓": "deep vein thrombosis OR DVT",
    "动脉粥样硬化": "atherosclerosis",
    "血管性痴呆": "vascular dementia",
    "化疗": "chemotherapy",
    "放疗": "radiotherapy OR radiation therapy",
    "靶向治疗": "targeted therapy",
    "免疫治疗": "immunotherapy",
    "干细胞移植": "stem cell transplantation",
    "器官移植": "organ transplantation",
    "血液透析": "hemodialysis",
    "腹膜透析": "peritoneal dialysis",
    "心肺复苏": "cardiopulmonary resuscitation OR CPR",
    "支架": "stent",
    "冠状动脉搭桥": "coronary artery bypass grafting OR CABG",
    "消融术": "ablation therapy",
    "射频消融": "radiofrequency ablation",
    "微创手术": "minimally invasive surgery",
    "腹腔镜手术": "laparoscopic surgery",
    "机器人手术": "robotic surgery",
    "基因治疗": "gene therapy",
    "细胞治疗": "cell therapy",
    "CAR-T": "CAR-T OR chimeric antigen receptor T cell",
    "单克隆抗体": "monoclonal antibody",
    "PD-1": "PD-1 OR programmed cell death protein 1",
    "免疫检查点抑制剂": "immune checkpoint inhibitor",
    "二甲双胍": "metformin",
    "胰岛素": "insulin",
    "他汀": "statin",
    "阿司匹林": "aspirin",
    "瑞德西韦": "remdesivir",
    "随机对照试验": "randomized controlled trial OR RCT",
    "系统评价": "systematic review",
    "荟萃分析": "meta-analysis",
    "Meta分析": "meta-analysis",
    "临床试验": "clinical trial",
    "队列研究": "cohort study",
    "病例对照研究": "case-control study",
    "横断面研究": "cross-sectional study",
    "病例报告": "case report",
    "前瞻性研究": "prospective study",
    "回顾性研究": "retrospective study",
    "动物实验": "animal experiment",
    "细胞实验": "in vitro OR cell experiment",
    "双盲": "double-blind",
    "安慰剂": "placebo",
    "比值比": "odds ratio OR OR",
    "风险比": "hazard ratio OR HR",
    "相对危险度": "relative risk OR RR",
    "森林图": "forest plot",
    "偏倚风险": "risk of bias",
    "PRISMA": "PRISMA",
    "GRADE": "GRADE",
    "诊断": "diagnosis",
    "治疗": "treatment OR therapy",
    "预后": "prognosis",
    "病因": "etiology",
    "发病机制": "pathogenesis OR mechanism",
    "病理生理": "pathophysiology",
    "生物标志物": "biomarker",
    "基因": "gene",
    "蛋白": "protein",
    "信号通路": "signaling pathway",
    "炎症因子": "inflammatory factor OR cytokine",
    "氧化应激": "oxidative stress",
    "细胞凋亡": "apoptosis",
    "血管生成": "angiogenesis",
    "转移": "metastasis",
    "耐药": "drug resistance",
    "疫苗": "vaccine OR vaccination",
    "炎症": "inflammation",
    "感染": "infection",
    "肠道菌群": "gut microbiome OR intestinal flora",
    "代谢组学": "metabolomics",
    "基因组学": "genomics",
    "蛋白质组学": "proteomics",
    "单细胞测序": "single-cell sequencing",
    "CRISPR": "CRISPR-Cas9",
    "基因编辑": "gene editing",
    "干细胞": "stem cell",
    "间充质干细胞": "mesenchymal stem cell OR MSC",
    "诱导多能干细胞": "iPSC OR induced pluripotent stem cell",
    "T细胞": "T cell",
    "B细胞": "B cell",
    "NK细胞": "NK cell OR natural killer cell",
    "巨噬细胞": "macrophage",
    "CAR-T细胞": "CAR-T cell",
    "外泌体": "exosome",
    "自噬": "autophagy",
    "铁死亡": "ferroptosis",
    "CT": "CT OR computed tomography",
    "MRI": "MRI OR magnetic resonance imaging",
    "超声": "ultrasound OR ultrasonography",
    "PET-CT": "PET-CT",
    "活检": "biopsy",
    "人工智能": "artificial intelligence OR AI",
    "机器学习": "machine learning",
    "深度学习": "deep learning",
    "神经网络": "neural network",
    "精准医疗": "precision medicine",
    "个体化医疗": "personalized medicine",
    "液体活检": "liquid biopsy",
    "基因检测": "genetic testing",
    "基因测序": "gene sequencing",
    "二代测序": "next-generation sequencing OR NGS",
    "PCR": "PCR OR polymerase chain reaction",
    "实时荧光PCR": "real-time PCR OR qPCR",
    "数字医疗": "digital health",
    "可穿戴设备": "wearable device",
    "远程医疗": "telemedicine",
    "生物信息学": "bioinformatics",
    "中医": "traditional Chinese medicine OR TCM",
    "中药": "Chinese herbal medicine",
    "针灸": "acupuncture",
    "太极拳": "tai chi",
    "疼痛": "pain",
    "发热": "fever OR pyrexia",
    "咳嗽": "cough",
    "呼吸困难": "dyspnea OR shortness of breath",
    "胸痛": "chest pain",
    "腹痛": "abdominal pain",
    "头痛": "headache",
    "水肿": "edema",
}


def translate_text(text: str, target_lang: str = "en", _retry: int = 3) -> str:
    """Translate text using MyMemory API (free, no API key needed)
    target_lang: 'en' for English, 'zh' for Chinese
    Has retry with exponential backoff for 429 (rate limit) responses.
    """
    if not text or not text.strip():
        return ""
    src = "zh-CN" if target_lang == "en" else "en"
    langpair = f"{src}|{target_lang}"
    encoded = urllib.parse.quote(text.strip())
    url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair={langpair}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    for attempt in range(_retry + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data.get("responseStatus") == 200:
                    translated = data.get("responseData", {}).get("translatedText", "")
                    if translated and translated.lower().replace(" ", "") != text.lower().replace(" ", ""):
                        return translated
                    return ""  # no valid translation, don't retry the same text
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < _retry:
                wait = (attempt + 1) * 3  # 3s, 6s, 9s
                print(f"  [MyMemory] Rate limited, retrying in {wait}s (attempt {attempt+1}/{_retry})")
                time.sleep(wait)
                continue
            print("Translation error:", e)
            return ""
        except Exception as e:
            print("Translation error:", e)
            return ""
    return ""


def detect_language(text: str) -> str:
    """Simple language detection: check for Chinese characters"""
    if not text:
        return "en"
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return "zh"
    return "en"


def translate_article_text(title: str, abstract: str) -> Dict[str, str]:
    """Translate article title and abstract to opposite language"""
    src_lang = detect_language(title)
    target_lang = "zh" if src_lang == "en" else "en"

    def translate_chunk(text: str) -> str:
        if not text:
            return ""
        # Split by Chinese period first (covers Chinese text)
        sentences = re.split(r'(?<=[。！？])\s*|(?<=[.!?])\s+', text.strip())
        translated = []
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            # Determine chunk language for accurate langpair
            chunk_lang = detect_language(s)
            chunk_target = "zh" if chunk_lang == "en" else "en"
            t = translate_text(s, chunk_target)
            if t:
                translated.append(t)
            else:
                translated.append(s)
        return ''.join(translated)

    title_translated = translate_chunk(title)
    abstract_translated = translate_chunk(abstract)

    # Always return: title_en=English, title_zh=Chinese
    # abstract_en=English, abstract_zh=Chinese
    result = {
        "title_en": "",
        "title_zh": "",
        "abstract_en": "",
        "abstract_zh": "",
    }
    if src_lang == "en":
        result["title_en"] = title
        result["title_zh"] = title_translated if title_translated and title_translated != title else ""
        result["abstract_en"] = abstract
        result["abstract_zh"] = abstract_translated if abstract_translated and abstract_translated != abstract else ""
    else:
        # Original is Chinese → translated goes to _en fields
        result["title_zh"] = title
        result["title_en"] = title_translated if title_translated and title_translated != title else ""
        result["abstract_zh"] = abstract
        result["abstract_en"] = abstract_translated if abstract_translated and abstract_translated != abstract else ""
    return result


def suggest_keywords(chinese_term: str) -> List[Dict[str, str]]:
    """Generate suggested search terms for a Chinese term"""
    suggestions = []
    seen = set()
    term = chinese_term.strip()

    if term in MEDICAL_TERMS:
        suggestions.append({
            "keyword": MEDICAL_TERMS[term],
            "type": "dictionary",
            "label": "标准术语"
        })
        seen.add(MEDICAL_TERMS[term])

    for cn, en in MEDICAL_TERMS.items():
        if cn != term and cn in term and en not in seen:
            suggestions.append({
                "keyword": en,
                "type": "component",
                "label": "组成词"
            })
            seen.add(en)

    api_translation = translate_text(term)
    if api_translation and api_translation not in seen:
        suggestions.append({
            "keyword": api_translation,
            "type": "api",
            "label": "AI翻译"
        })

    return suggestions[:8]


# ============================================================================
# PubMed API Functions
# ============================================================================

def search_pubmed(query: str, max_results: int = 20, sort: str = "relevance",
                  year_min: str = "", year_max: str = "", article_types: List[str] = None) -> Dict[str, Any]:
    """Search PubMed and return dict with pmids list and total count"""
    filters = []
    if year_min and year_max:
        filters.append(year_min + ":" + year_max + "[dp]")
    elif year_min:
        filters.append(year_min + "[dp]")
    elif year_max:
        filters.append(year_max + "[dp]")
    if article_types:
        for at in article_types:
            if at:
                filters.append(at + "[pt]")
    if filters:
        combined = urllib.parse.quote(query) + " " + " ".join(filters)
    else:
        combined = urllib.parse.quote(query)
    url = BASE_URL + "/esearch.fcgi?db=pubmed&term=" + combined + "&retmax=" + str(max_results) + "&sort=" + sort + "&retmode=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            esr = data.get("esearchresult", {})
            pmids = esr.get("idlist", [])
            count = int(esr.get("count", 0))
            return {"pmids": pmids, "count": count}
    except Exception as e:
        print("Search error:", e)
        return {"pmids": [], "count": 0}


def fetch_article_details(pmids: List[str], task_id: str = None) -> List[Dict[str, Any]]:
    if not pmids:
        return []
    all_articles = []
    batch_size = 100
    total_batches = (len(pmids) + batch_size - 1) // batch_size
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i+batch_size]
        ids = ",".join(batch)
        url = BASE_URL + "/esummary.fcgi?db=pubmed&id=" + ids + "&retmode=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
                result = data.get("result", {})
                for pmid in batch:
                    if pmid in result:
                        article = result[pmid]
                        authors = article.get("authors", [])
                        author_names = [a.get("name", "") for a in authors[:5] if a.get("name")]
                        all_articles.append({
                            "pmid": pmid,
                            "title": article.get("title", "N/A"),
                            "authors": author_names,
                            "author_count": len(authors),
                            "all_authors": [a.get("name", "") for a in authors if a.get("name")],
                            "journal": article.get("fulljournalname", article.get("source", "N/A")),
                            "pubdate": article.get("pubdate", "N/A"),
                            "pubtype": article.get("pubtype", []),
                            "doi": article.get("elocationid", "").replace("doi: ", ""),
                            "volume": article.get("volume", ""),
                            "issue": article.get("issue", ""),
                            "pages": article.get("pages", ""),
                            "pmcid": article.get("pmcid", ""),
                            "lang": article.get("lang", []),
                        })
        except Exception as e:
            print("Batch fetch error:", e)
        if task_id and task_id in tasks:
            batch_num = i // batch_size + 1
            tasks[task_id]["phase"] = "details"
            tasks[task_id]["progress"] = int(batch_num / total_batches * 45)
        if i + batch_size < len(pmids):
            time.sleep(0.34)
    return all_articles


def fetch_abstracts(pmids: List[str], task_id: str = None) -> Dict[str, str]:
    """Fetch abstracts using XML format for reliable parsing."""
    if not pmids:
        return {}
    all_abstracts = {}
    batch_size = 200
    total_batches = (len(pmids) + batch_size - 1) // batch_size
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i+batch_size]
        ids = ",".join(batch)
        url = BASE_URL + "/efetch.fcgi?db=pubmed&id=" + ids + "&rettype=abstract&retmode=xml"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read().decode("utf-8")
                try:
                    root = ET.fromstring(content)
                    for article in root.findall(".//PubmedArticle"):
                        pmid_elem = article.find(".//PMID")
                        if pmid_elem is None:
                            continue
                        pmid = pmid_elem.text
                        abstract_elems = article.findall(".//AbstractText")
                        parts = []
                        for ab in abstract_elems:
                            text = ab.text or ""
                            if text.strip():
                                parts.append(text.strip())
                        all_abstracts[pmid] = " ".join(parts)
                except ET.ParseError as e:
                    print("XML parse error:", e)
        except Exception as e:
            print("Abstract batch error:", e)
        if task_id and task_id in tasks:
            batch_num = i // batch_size + 1
            tasks[task_id]["phase"] = "abstracts"
            tasks[task_id]["progress"] = 45 + int(batch_num / total_batches * 45)
        if i + batch_size < len(pmids):
            time.sleep(0.34)
    return all_abstracts


INITIAL_BATCH = 100  # first batch to load immediately
MORE_BATCH = 100     # subsequent batches on scroll


def run_search_task(task_id: str, query: str, max_results: int, sort: str,
                    year_min: str, year_max: str, article_types: List[str]):
    try:
        tasks[task_id]["phase"] = "searching"
        tasks[task_id]["progress"] = 0

        # 1. PubMed search (fast)
        search_result = search_pubmed(query, max_results, sort, year_min, year_max, article_types)
        pmids = search_result["pmids"]
        total_count = search_result["count"]

        tasks[task_id]["total"] = total_count
        tasks[task_id]["pmids"] = pmids
        tasks[task_id]["loaded"] = 0
        tasks[task_id]["remaining_pmids"] = []

        # 2. Load first batch immediately
        if not pmids:
            tasks[task_id]["articles"] = []
            tasks[task_id]["status"] = "done"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["phase"] = "done"
            return

        first_batch = pmids[:INITIAL_BATCH]
        rest_pmids = pmids[INITIAL_BATCH:]
        tasks[task_id]["remaining_pmids"] = rest_pmids

        # fetch details + abstracts for first batch
        details = fetch_article_details(first_batch, task_id)
        abstracts = fetch_abstracts(first_batch, task_id)
        for a in details:
            a["abstract"] = abstracts.get(a["pmid"], "")

        tasks[task_id]["articles"] = details
        tasks[task_id]["loaded"] = len(first_batch)
        tasks[task_id]["status"] = "done"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["phase"] = "done"

    except Exception as e:
        print("Task error:", e)
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)


# ============================================================================
# API Routes
# ============================================================================

@app.route("/")
@app.route("/index.html")
def index():
    try:
        html_path = os.path.join(STATIC_DIR, "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return add_cors_headers(response)
    except Exception as e:
        print("Error serving index.html:", e)
        return "Error loading page", 500


@app.route("/api/translate", methods=["POST", "OPTIONS"])
def api_translate():
    data = request.get_json() or {}
    term = data.get("term", "").strip()
    if not term:
        return add_cors_headers(jsonify({"suggestions": []}))
    suggestions = suggest_keywords(term)
    return add_cors_headers(jsonify({"suggestions": suggestions, "term": term}))


@app.route("/api/article/translate", methods=["POST"])
def api_article_translate():
    """Translate article titles and abstracts.
    Body: { "articles": [{ "pmid": "...", "title": "...", "abstract": "..." }] }
    Returns: { "translations": { "pmid": { "title_en": ..., "title_zh": ..., "abstract_en": ..., "abstract_zh": ... } } }
    """
    data = request.get_json() or {}
    articles = data.get("articles", [])
    if not articles:
        return add_cors_headers(jsonify({"translations": {}}))

    translations = {}
    for article in articles:
        pmid = str(article.get("pmid", ""))
        title = article.get("title", "") or ""
        abstract = article.get("abstract", "") or ""
        translations[pmid] = translate_article_text(title, abstract)
        # Small delay to avoid rate limiting MyMemory API
        time.sleep(0.3)

    return add_cors_headers(jsonify({"translations": translations}))


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    max_results = min(int(data.get("max_results", 100)), 10000)
    sort = data.get("sort", "relevance")
    year_min = data.get("year_min", "")
    year_max = data.get("year_max", "")
    article_types = data.get("article_types", [])
    if not query:
        return jsonify({"error": "请输入搜索关键词"}), 400
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "status": "running", "progress": 0, "phase": "initializing",
        "articles": [], "total": 0, "query": query
    }
    thread = threading.Thread(
        target=run_search_task,
        args=(task_id, query, max_results, sort, year_min, year_max, article_types)
    )
    thread.daemon = True
    thread.start()
    return jsonify({"task_id": task_id, "status": "running"})


@app.route("/api/task/<task_id>")
def get_task(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    remaining = task.get("remaining_pmids", [])
    pmids = task.get("pmids", [])
    return jsonify({
        "status": task.get("status", "running"),
        "progress": task.get("progress", 0),
        "phase": task.get("phase", ""),
        "total": task.get("total", 0),
        "count": task.get("total", 0),
        "loaded": task.get("loaded", 0),
        "pmids_count": len(pmids),
        "remaining_count": len(remaining),
        "has_more": len(remaining) > 0,
        "articles": task.get("articles", []),
        "query": task.get("query", "")
    })


@app.route("/api/task/<task_id>/more", methods=["GET"])
def api_task_more(task_id):
    """Load next batch of article details (lazy load on scroll)"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    remaining = task.get("remaining_pmids", [])
    if not remaining:
        return jsonify({"articles": [], "has_more": False, "loaded": task.get("loaded", 0)})

    # take next batch
    batch = remaining[:MORE_BATCH]
    new_remaining = remaining[MORE_BATCH:]
    task["remaining_pmids"] = new_remaining
    task["loaded"] = task.get("loaded", 0) + len(batch)

    # fetch details + abstracts
    details = fetch_article_details(batch, task_id)
    abstracts = fetch_abstracts(batch, task_id)
    for a in details:
        a["abstract"] = abstracts.get(a["pmid"], "")

    task["articles"].extend(details)
    return jsonify({
        "articles": details,
        "has_more": len(new_remaining) > 0,
        "loaded": task.get("loaded", 0),
        "remaining_count": len(new_remaining),
        "total": task.get("total", 0)
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  PubMed Literature Search  -  v6.0")
    print("  Backend (separate file + HTML)")
    print("=" * 60)
    print("  Open: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
