STANDARD_CONTRACT_RESOURCES = [
    {
        "id": "itc-model-contracts",
        "title": "ITC Model Contracts for Small Firms",
        "category": "무료·영문 표준계약",
        "group": "무역·구매",
        "description": "중소기업이 국제무역에서 바로 활용하기 좋은 매매·대리점·위탁제조·NDA 등의 영문 템플릿 모음입니다.",
        "detail": "ITC가 중소기업용으로 정리한 자료로, 국제거래에서 자주 쓰는 핵심 조항을 빠르게 참조할 수 있습니다. 특히 수출입, 유통, 위탁생산, 기업간 비밀유지 계약의 출발점으로 유용합니다.",
        "url": "https://www.intracen.org/resources/publications/model-contracts-for-small-firms",
        "tags": ["ITC", "무료", "영문", "무역"],
    },
    {
        "id": "icc-model-contracts",
        "title": "ICC Model Contracts",
        "category": "국제거래 표준계약",
        "group": "국제상사계약",
        "description": "국제매매·판매점·대리점·프랜차이즈 등에서 널리 쓰이는 국제 상사계약 표준서식입니다.",
        "detail": "국제 분쟁 시 신뢰도가 높고, 국제매매와 유통계약에서 자주 참고되는 권위 있는 템플릿입니다. 다만 준거법과 중재지 등은 거래상황에 맞게 수정해야 합니다.",
        "url": "https://2go.iccwbo.org",
        "tags": ["ICC", "국제거래", "유료"],
    },
    {
        "id": "korea-export-support",
        "title": "KITA·KOTRA·법무부 해외진출 자료",
        "category": "국내 기관 지원자료",
        "group": "국내 실무지원",
        "description": "한국무역협회, 코트라, 법무부의 무역·법률 자문 및 영문 계약서 관련 실무자료를 한눈에 확인할 수 있습니다.",
        "detail": "국내에서 수출·해외진출을 준비할 때 가장 현실적인 출발점입니다. 수출바우처, 법률자문, 계약서 번역 지원 등 실무 리소스를 한데 모아볼 수 있습니다.",
        "url": "https://www.kita.net",
        "tags": ["KITA", "KOTRA", "법무부", "지원자료"],
    },
]


def build_standard_contract_seed_docs():
    return [
        {
            "doc_id": "STD-ITC-001",
            "clause_type": "표준계약서",
            "text": "ITC Model Contracts for Small Firms는 중소기업이 국제무역에서 활용하기 좋은 무료 영문 표준계약서 모음으로, 국제물품매매·판매점·대리점·위탁제조·합작투자·비밀유지 계약을 포함한다. 해외 사업에서 처음 계약서를 준비하는 기업이 비교적 쉽게 접근할 수 있는 실무 자료다.",
        },
        {
            "doc_id": "STD-ICC-001",
            "clause_type": "표준계약서",
            "text": "ICC Model Contracts는 국제거래에서 널리 통용되는 상사계약 표준서식으로, 국제매매와 유통·대리점·프랜차이즈 분야에서 신뢰도가 높다. 실제 체결 전에는 계약 상대국과 거래 유형에 맞게 준거법·중재·CISG 적용 여부를 반드시 확인해야 한다.",
        },
        {
            "doc_id": "STD-KR-001",
            "clause_type": "표준계약서",
            "text": "KITA, KOTRA, 법무부 등 국내 기관은 해외진출 중소기업을 위해 무역 실무자료와 영문계약서 자문, 수출바우처 지원 등을 제공한다. 우리 기업은 표준서식을 참고하되, 최종 계약은 현지 강행규정과 분쟁해결 조항을 함께 검토해야 한다.",
        },
        {
            "doc_id": "STD-CAUTION-001",
            "clause_type": "표준계약서",
            "text": "표준계약서는 유용하나 준거법, 중재지, CISG 적용 여부, 현지 강행규정, 지체상금·해지보상금 등 핵심 조항은 반드시 거래 상대국과 사업 리스크에 맞게 수정해야 한다. 실제 체결 전에는 변호사 검토가 권장된다.",
        },
    ]
