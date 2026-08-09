"""SME/스타트업용 영문 표준계약서 자동생성 질문지 정의.

각 템플릿은 knowledge/standard-contract 자료(패밀리)를 근거로 하며,
사용자가 입력한 답변으로 LLM이 초안을 생성할 때 그대로 프롬프트에 포함된다.
"""

COMMON_FIELDS = [
    {
        "key": "party_a_name",
        "label": "당사(귀사) 회사명",
        "type": "text",
        "required": True,
        "placeholder": "예: ABC Corp.",
    },
    {
        "key": "party_a_country",
        "label": "당사 소재국",
        "type": "text",
        "required": True,
        "placeholder": "예: Republic of Korea",
    },
    {
        "key": "party_b_name",
        "label": "상대방 회사명",
        "type": "text",
        "required": True,
        "placeholder": "예: XYZ Inc.",
    },
    {
        "key": "party_b_country",
        "label": "상대방 소재국",
        "type": "text",
        "required": True,
        "placeholder": "예: State of Delaware, USA",
    },
    {
        "key": "effective_date",
        "label": "계약 발효일",
        "type": "date",
        "required": True,
    },
    {
        "key": "governing_law",
        "label": "준거법",
        "type": "text",
        "required": True,
        "placeholder": "예: State of New York, USA",
    },
    {
        "key": "dispute_resolution",
        "label": "분쟁해결 방식",
        "type": "select",
        "required": True,
        "options": [
            {"value": "arbitration", "label": "중재 (Arbitration)"},
            {"value": "litigation", "label": "소송 (Litigation)"},
        ],
    },
    {
        "key": "arbitration_seat",
        "label": "중재지 / 관할법원 소재지",
        "type": "text",
        "required": False,
        "placeholder": "예: Singapore (SIAC) 또는 관할법원 소재지",
    },
]

CONTRACT_TEMPLATES = [
    {
        "id": "mutual-nda",
        "title": "비밀유지계약서 (Mutual NDA)",
        "family": "NDA",
        "description": "초기 상담·샘플 교환·기술 논의 단계에서 상호 비밀정보를 보호하기 위한 영문 NDA입니다.",
        "fields": COMMON_FIELDS + [
            {
                "key": "purpose",
                "label": "정보 공유 목적",
                "type": "textarea",
                "required": True,
                "placeholder": "예: 제품 공급 가능성 검토를 위한 기술·가격 정보 교환",
            },
            {
                "key": "term_years",
                "label": "비밀유지 기간(년)",
                "type": "number",
                "required": True,
                "placeholder": "예: 3",
            },
        ],
    },
    {
        "id": "international-distributor-agreement",
        "title": "해외 유통·대리점 계약 (International Distributor Agreement)",
        "family": "DISTRIBUTOR",
        "description": "해외 총판·대리점을 지정해 제품을 유통시킬 때 사용하는 영문 계약서입니다.",
        "fields": COMMON_FIELDS + [
            {
                "key": "products",
                "label": "대상 제품",
                "type": "textarea",
                "required": True,
            },
            {
                "key": "territory",
                "label": "판매 구역 (Territory)",
                "type": "text",
                "required": True,
                "placeholder": "예: United States and Canada",
            },
            {
                "key": "exclusivity",
                "label": "독점 여부",
                "type": "select",
                "required": True,
                "options": [
                    {"value": "exclusive", "label": "독점 (Exclusive)"},
                    {"value": "non-exclusive", "label": "비독점 (Non-Exclusive)"},
                ],
            },
            {
                "key": "minimum_purchase",
                "label": "최소구매수량/금액 (연간)",
                "type": "text",
                "required": False,
                "placeholder": "예: USD 500,000 per year",
            },
            {
                "key": "term_years",
                "label": "계약 기간(년)",
                "type": "number",
                "required": True,
                "placeholder": "예: 2",
            },
        ],
    },
    {
        "id": "oem-odm-manufacturing-agreement",
        "title": "OEM/ODM 위탁생산 계약 (OEM/ODM Manufacturing Agreement)",
        "family": "OEM/ODM",
        "description": "해외 브랜드사·제조사와 위탁생산 관계를 맺을 때 사용하는 영문 계약서입니다.",
        "fields": COMMON_FIELDS + [
            {
                "key": "products",
                "label": "생산 대상 제품",
                "type": "textarea",
                "required": True,
            },
            {
                "key": "ip_ownership",
                "label": "설계자산(금형·설계도) 귀속",
                "type": "select",
                "required": True,
                "options": [
                    {"value": "buyer", "label": "Buyer(발주사) 귀속"},
                    {"value": "manufacturer", "label": "Manufacturer(제조사) 귀속"},
                ],
            },
            {
                "key": "quality_standard",
                "label": "품질기준 / 검사기준",
                "type": "text",
                "required": False,
                "placeholder": "예: ISO 9001, AQL 1.5",
            },
            {
                "key": "minimum_order_quantity",
                "label": "최소생산수량 (MOQ)",
                "type": "text",
                "required": False,
                "placeholder": "예: 10,000 units per order",
            },
            {
                "key": "term_years",
                "label": "계약 기간(년)",
                "type": "number",
                "required": True,
                "placeholder": "예: 3",
            },
        ],
    },
    {
        "id": "license-agreement",
        "title": "기술·브랜드 라이선스 계약 (License Agreement)",
        "family": "LICENSE",
        "description": "기술, 상표, 소프트웨어 등 지식재산을 해외 파트너에게 라이선스할 때 사용하는 영문 계약서입니다.",
        "fields": COMMON_FIELDS + [
            {
                "key": "licensed_ip",
                "label": "라이선스 대상 IP",
                "type": "textarea",
                "required": True,
                "placeholder": "예: 특허 제10-XXXXXXX호, 상표 'ABC'",
            },
            {
                "key": "license_scope",
                "label": "라이선스 범위",
                "type": "select",
                "required": True,
                "options": [
                    {"value": "exclusive", "label": "독점 (Exclusive)"},
                    {"value": "non-exclusive", "label": "비독점 (Non-Exclusive)"},
                ],
            },
            {
                "key": "royalty_rate",
                "label": "로열티율",
                "type": "text",
                "required": True,
                "placeholder": "예: 순매출액의 5%",
            },
            {
                "key": "minimum_guarantee",
                "label": "최소보장금 (MG)",
                "type": "text",
                "required": False,
                "placeholder": "예: USD 50,000 per year",
            },
            {
                "key": "term_years",
                "label": "계약 기간(년)",
                "type": "number",
                "required": True,
                "placeholder": "예: 5",
            },
        ],
    },
    {
        "id": "saas-license-agreement",
        "title": "SaaS 구독 라이선스 계약 (SaaS License Agreement)",
        "family": "KR-TRADE-FORMS",
        "description": "해외 고객사에 구독형 소프트웨어 서비스를 제공할 때 사용하는 영문 계약서입니다.",
        "fields": COMMON_FIELDS + [
            {
                "key": "service_description",
                "label": "서비스 개요",
                "type": "textarea",
                "required": True,
            },
            {
                "key": "sla_uptime",
                "label": "SLA 가동률 목표",
                "type": "text",
                "required": False,
                "placeholder": "예: 99.5% monthly uptime",
            },
            {
                "key": "subscription_fee",
                "label": "구독료",
                "type": "text",
                "required": True,
                "placeholder": "예: USD 2,000 per month",
            },
            {
                "key": "data_location",
                "label": "데이터 처리·저장 위치",
                "type": "text",
                "required": False,
                "placeholder": "예: AWS ap-northeast-2 (Seoul)",
            },
            {
                "key": "term_years",
                "label": "계약 기간(년)",
                "type": "number",
                "required": True,
                "placeholder": "예: 1",
            },
        ],
    },
    {
        "id": "supply-agreement",
        "title": "국제물품공급 계약 (International Supply Agreement)",
        "family": "SALE-OF-GOODS",
        "description": "해외 바이어에게 물품을 지속적으로 공급할 때 사용하는 영문 계약서로, CISG 적용 여부를 함께 점검합니다.",
        "fields": COMMON_FIELDS + [
            {
                "key": "products",
                "label": "공급 대상 물품",
                "type": "textarea",
                "required": True,
            },
            {
                "key": "incoterm",
                "label": "인도조건 (Incoterms)",
                "type": "text",
                "required": True,
                "placeholder": "예: FOB Busan (Incoterms 2020)",
            },
            {
                "key": "price",
                "label": "단가/대금조건",
                "type": "text",
                "required": True,
                "placeholder": "예: USD 12.50 per unit, T/T 30 days",
            },
            {
                "key": "minimum_order_quantity",
                "label": "최소주문수량 (MOQ)",
                "type": "text",
                "required": False,
            },
            {
                "key": "cisg_opt_out",
                "label": "CISG(비엔나협약) 적용 배제 여부",
                "type": "select",
                "required": True,
                "options": [
                    {"value": "apply", "label": "CISG 적용 (배제하지 않음)"},
                    {"value": "opt-out", "label": "CISG 명시적 배제"},
                ],
            },
            {
                "key": "term_years",
                "label": "계약 기간(년)",
                "type": "number",
                "required": True,
                "placeholder": "예: 2",
            },
        ],
    },
]


def get_template(template_id: str) -> dict | None:
    for t in CONTRACT_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None


def list_templates() -> list[dict]:
    return CONTRACT_TEMPLATES
