"""Reference prompt suite for OCI architecture diagram validation.

The cases are intentionally deterministic: they are not a natural-language
parser, but a broad set of compound prompts paired with normalized specs that
exercise the renderer across common OCI Architecture Center patterns.
"""

from __future__ import annotations

import copy
from typing import Any


VARIANTS = [
    {
        "theme": "produccion publica",
        "constraint": "alta disponibilidad, acceso publico controlado y trazabilidad",
        "addon": ("monitoring", "Monitoring", "Monitoring", "ops-subnet", "observability"),
    },
    {
        "theme": "carga regulada",
        "constraint": "segmentacion, cifrado y auditoria para cumplimiento",
        "addon": ("vault", "Vault", "Vault", "ops-subnet", "secrets"),
    },
    {
        "theme": "operacion financiera",
        "constraint": "flujos privados, bitacoras centralizadas y recuperacion rapida",
        "addon": ("logging", "Logging", "Logging", "ops-subnet", "logs"),
    },
    {
        "theme": "plataforma con eventos",
        "constraint": "procesamiento asincrono y desacoplamiento entre servicios",
        "addon": ("events", "Events", "Events", "ops-subnet", "events"),
    },
    {
        "theme": "canal de notificaciones",
        "constraint": "alertas operativas y comunicacion de fallas",
        "addon": ("notifications", "Notifications", "Notifications", "ops-subnet", "alerts"),
    },
    {
        "theme": "entrega continua",
        "constraint": "pipeline de despliegue y cambios repetibles",
        "addon": ("devops", "DevOps", "DevOps", "ops-subnet", "deploys"),
    },
    {
        "theme": "proteccion de datos",
        "constraint": "revision de riesgos y gobierno de datos sensibles",
        "addon": ("data-safe", "Data Safe", "Data Safe", "ops-subnet", "data checks"),
    },
    {
        "theme": "correo transaccional",
        "constraint": "notificaciones externas sin exponer la red privada",
        "addon": ("email-delivery", "Email Delivery", "Email Delivery", "ops-subnet", "mail"),
    },
    {
        "theme": "entrada con DNS",
        "constraint": "resolucion de nombres y entrada limpia hacia la aplicacion",
        "addon": ("dns", "DNS", "DNS", "public-subnet", "dns"),
    },
    {
        "theme": "administracion segura",
        "constraint": "acceso temporal a recursos privados sin IP publica",
        "addon": ("bastion", "Bastion", "Bastion", "ops-subnet", "admin"),
    },
]


BASE_ARCHITECTURES: list[dict[str, Any]] = [
    {
        "name": "web-oke-adb",
        "summary": "aplicacion web publica con OKE, base autonoma y bucket",
        "groups": [
            {"id": "region", "label": "OCI Region", "type": "region"},
            {"id": "vcn", "label": "Application VCN", "type": "vcn", "parent": "region"},
            {"id": "public-subnet", "label": "Public Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "private-subnet", "label": "Private App Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "data-subnet", "label": "Private Data Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "ops-subnet", "label": "Operations Subnet", "type": "subnet", "parent": "vcn"},
        ],
        "nodes": [
            {"id": "dns-main", "label": "Public DNS", "service": "DNS", "group": "public-subnet"},
            {"id": "waf-main", "label": "Edge WAF", "service": "WAF", "group": "public-subnet"},
            {"id": "lb-main", "label": "Public Load Balancer", "service": "Load Balancer", "group": "public-subnet"},
            {"id": "oke-main", "label": "Application Pods", "service": "OKE", "group": "private-subnet"},
            {"id": "adb-main", "label": "Autonomous Database", "service": "Oracle Autonomous Database", "group": "data-subnet"},
            {"id": "obj-main", "label": "Static Assets", "service": "Object Storage", "group": "data-subnet"},
        ],
        "edges": [
            {"from": "dns-main", "to": "waf-main", "label": "DNS"},
            {"from": "waf-main", "to": "lb-main", "label": "HTTPS"},
            {"from": "lb-main", "to": "oke-main", "label": "HTTP"},
            {"from": "oke-main", "to": "adb-main", "label": "SQL"},
            {"from": "oke-main", "to": "obj-main", "label": "SDK"},
        ],
        "addon_from": "oke-main",
    },
    {
        "name": "three-tier-compute",
        "summary": "arquitectura de tres capas con compute y base de datos",
        "groups": [
            {"id": "region", "label": "OCI Region", "type": "region"},
            {"id": "vcn", "label": "Enterprise VCN", "type": "vcn", "parent": "region"},
            {"id": "public-subnet", "label": "Public Web Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "private-subnet", "label": "Private App Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "data-subnet", "label": "Private DB Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "ops-subnet", "label": "Operations Subnet", "type": "subnet", "parent": "vcn"},
        ],
        "nodes": [
            {"id": "dns-main", "label": "DNS Zone", "service": "DNS", "group": "public-subnet"},
            {"id": "waf-main", "label": "Web Application Firewall", "service": "WAF", "group": "public-subnet"},
            {"id": "lb-main", "label": "Load Balancer", "service": "Load Balancer", "group": "public-subnet"},
            {"id": "web-vm", "label": "Web Tier VM", "service": "Virtual Machine", "group": "private-subnet"},
            {"id": "app-vm", "label": "App Tier VM", "service": "Virtual Machine", "group": "private-subnet"},
            {"id": "db-main", "label": "Base Database", "service": "Oracle Base Database", "group": "data-subnet"},
            {"id": "files", "label": "Shared File Storage", "service": "File Storage", "group": "data-subnet"},
        ],
        "edges": [
            {"from": "dns-main", "to": "waf-main", "label": "DNS"},
            {"from": "waf-main", "to": "lb-main", "label": "HTTPS"},
            {"from": "lb-main", "to": "web-vm", "label": "HTTP"},
            {"from": "web-vm", "to": "app-vm", "label": "API"},
            {"from": "app-vm", "to": "db-main", "label": "SQL"},
            {"from": "app-vm", "to": "files", "label": "NFS"},
        ],
        "addon_from": "app-vm",
    },
    {
        "name": "hub-spoke-network",
        "summary": "red hub-and-spoke con conectividad hibrida y seguridad central",
        "groups": [
            {"id": "onprem", "label": "On-premises", "type": "group"},
            {"id": "region", "label": "OCI Region", "type": "region"},
            {"id": "hub-vcn", "label": "Hub VCN", "type": "vcn", "parent": "region"},
            {"id": "spoke-a", "label": "Prod Spoke VCN", "type": "vcn", "parent": "region"},
            {"id": "spoke-b", "label": "Nonprod Spoke VCN", "type": "vcn", "parent": "region"},
            {"id": "ops-subnet", "label": "Shared Services", "type": "subnet", "parent": "hub-vcn"},
        ],
        "nodes": [
            {"id": "onprem-dc", "label": "Data Center", "service": "On-premises Data Center", "group": "onprem"},
            {"id": "fastconnect", "label": "FastConnect", "service": "FastConnect", "group": "hub-vcn"},
            {"id": "vpn", "label": "Site-to-Site VPN", "service": "Site-to-Site VPN", "group": "hub-vcn"},
            {"id": "drg", "label": "Dynamic Routing Gateway", "service": "DRG", "group": "hub-vcn"},
            {"id": "firewall", "label": "Network Firewall", "service": "Firewall", "group": "ops-subnet"},
            {"id": "lpg-a", "label": "Prod LPG", "service": "Local Peering Gateway", "group": "spoke-a"},
            {"id": "lpg-b", "label": "Nonprod LPG", "service": "Local Peering Gateway", "group": "spoke-b"},
            {"id": "prod-vm", "label": "Prod VM", "service": "Virtual Machine", "group": "spoke-a"},
            {"id": "nonprod-vm", "label": "Nonprod VM", "service": "Virtual Machine", "group": "spoke-b"},
        ],
        "edges": [
            {"from": "onprem-dc", "to": "fastconnect", "label": "private"},
            {"from": "onprem-dc", "to": "vpn", "label": "backup"},
            {"from": "fastconnect", "to": "drg", "label": "BGP"},
            {"from": "vpn", "to": "drg", "label": "IPSec"},
            {"from": "drg", "to": "firewall", "label": "inspect"},
            {"from": "firewall", "to": "lpg-a", "label": "peer"},
            {"from": "firewall", "to": "lpg-b", "label": "peer"},
            {"from": "lpg-a", "to": "prod-vm", "label": "private"},
            {"from": "lpg-b", "to": "nonprod-vm", "label": "private"},
        ],
        "addon_from": "firewall",
    },
    {
        "name": "data-lakehouse",
        "summary": "lakehouse con ingesta streaming, object storage, ADW y analytics",
        "groups": [
            {"id": "region", "label": "OCI Region", "type": "region"},
            {"id": "vcn", "label": "Data Platform VCN", "type": "vcn", "parent": "region"},
            {"id": "ingest-subnet", "label": "Ingestion Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "data-subnet", "label": "Data Services Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "consumer-subnet", "label": "Consumer Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "ops-subnet", "label": "Governance Subnet", "type": "subnet", "parent": "vcn"},
        ],
        "nodes": [
            {"id": "streaming", "label": "Event Streams", "service": "Streaming", "group": "ingest-subnet"},
            {"id": "data-integration", "label": "Data Integration", "service": "Data Integration", "group": "ingest-subnet"},
            {"id": "data-flow", "label": "Spark Processing", "service": "Data Flow", "group": "data-subnet"},
            {"id": "object-storage", "label": "Lake Buckets", "service": "Object Storage", "group": "data-subnet"},
            {"id": "adw", "label": "Autonomous Data Warehouse", "service": "Oracle Autonomous Data Warehouse", "group": "data-subnet"},
            {"id": "catalog", "label": "Data Catalog", "service": "Data Catalog", "group": "ops-subnet"},
            {"id": "analytics", "label": "Analytics", "service": "Analytics", "group": "consumer-subnet"},
            {"id": "data-science", "label": "ML Workbench", "service": "Data Science", "group": "consumer-subnet"},
        ],
        "edges": [
            {"from": "streaming", "to": "data-flow", "label": "stream"},
            {"from": "data-integration", "to": "object-storage", "label": "batch"},
            {"from": "data-flow", "to": "object-storage", "label": "curate"},
            {"from": "object-storage", "to": "adw", "label": "external tables"},
            {"from": "catalog", "to": "object-storage", "label": "metadata"},
            {"from": "adw", "to": "analytics", "label": "SQL"},
            {"from": "adw", "to": "data-science", "label": "features"},
        ],
        "addon_from": "catalog",
    },
    {
        "name": "multicloud-api",
        "summary": "API Gateway conectando microservicios OCI, externos y base autonoma",
        "groups": [
            {"id": "external", "label": "External Services", "type": "group"},
            {"id": "region", "label": "OCI Region", "type": "region"},
            {"id": "vcn", "label": "Integration VCN", "type": "vcn", "parent": "region"},
            {"id": "public-subnet", "label": "API Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "private-subnet", "label": "Service Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "data-subnet", "label": "Data Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "ops-subnet", "label": "Operations Subnet", "type": "subnet", "parent": "vcn"},
        ],
        "nodes": [
            {"id": "partner", "label": "Partner Cloud", "service": "On-premises Data Center", "group": "external"},
            {"id": "api", "label": "API Gateway", "service": "API Gateway", "group": "public-subnet"},
            {"id": "functions", "label": "Functions", "service": "Functions", "group": "private-subnet"},
            {"id": "oke", "label": "Container Services", "service": "OKE", "group": "private-subnet"},
            {"id": "service-gateway", "label": "Service Gateway", "service": "Service Gateway", "group": "private-subnet"},
            {"id": "adb", "label": "Autonomous Database", "service": "Oracle Autonomous Database", "group": "data-subnet"},
            {"id": "bucket", "label": "Exchange Bucket", "service": "Object Storage", "group": "data-subnet"},
        ],
        "edges": [
            {"from": "partner", "to": "api", "label": "REST"},
            {"from": "api", "to": "functions", "label": "invoke"},
            {"from": "api", "to": "oke", "label": "route"},
            {"from": "functions", "to": "adb", "label": "SQL"},
            {"from": "oke", "to": "service-gateway", "label": "private"},
            {"from": "service-gateway", "to": "bucket", "label": "object API"},
        ],
        "addon_from": "api",
    },
    {
        "name": "ebs-disaster-recovery",
        "summary": "Oracle E-Business Suite con DR multi-region y Data Guard",
        "groups": [
            {"id": "primary-region", "label": "Primary OCI Region", "type": "region"},
            {"id": "primary-vcn", "label": "Primary VCN", "type": "vcn", "parent": "primary-region"},
            {"id": "secondary-region", "label": "Standby OCI Region", "type": "region"},
            {"id": "secondary-vcn", "label": "Standby VCN", "type": "vcn", "parent": "secondary-region"},
            {"id": "ops-subnet", "label": "DR Operations", "type": "subnet", "parent": "primary-vcn"},
        ],
        "nodes": [
            {"id": "primary-lb", "label": "Primary Load Balancer", "service": "Load Balancer", "group": "primary-vcn"},
            {"id": "primary-app", "label": "EBS App Tier", "service": "Virtual Machine", "group": "primary-vcn"},
            {"id": "primary-db", "label": "Primary Database", "service": "Oracle Base Database", "group": "primary-vcn"},
            {"id": "primary-files", "label": "Shared File Storage", "service": "File Storage", "group": "primary-vcn"},
            {"id": "data-guard", "label": "Data Guard", "service": "Data Guard", "group": "ops-subnet"},
            {"id": "fsdr", "label": "Full Stack DR", "service": "Full Stack Disaster Recovery", "group": "ops-subnet"},
            {"id": "standby-app", "label": "Standby App Tier", "service": "Virtual Machine", "group": "secondary-vcn"},
            {"id": "standby-db", "label": "Standby Database", "service": "Oracle Base Database", "group": "secondary-vcn"},
        ],
        "edges": [
            {"from": "primary-lb", "to": "primary-app", "label": "HTTP"},
            {"from": "primary-app", "to": "primary-db", "label": "SQL"},
            {"from": "primary-app", "to": "primary-files", "label": "NFS"},
            {"from": "primary-db", "to": "data-guard", "label": "redo"},
            {"from": "data-guard", "to": "standby-db", "label": "replicate"},
            {"from": "fsdr", "to": "standby-app", "label": "orchestrate"},
            {"from": "fsdr", "to": "standby-db", "label": "failover"},
        ],
        "addon_from": "fsdr",
    },
    {
        "name": "cyber-resilience",
        "summary": "enclaves de resiliencia con backups inmutables y restore seguro",
        "groups": [
            {"id": "prod-enclave", "label": "Production Enclave", "type": "vcn"},
            {"id": "vault-enclave", "label": "Vault Enclave", "type": "vcn"},
            {"id": "safe-restore", "label": "Safe Restore Enclave", "type": "vcn"},
            {"id": "ops-subnet", "label": "Cyber Operations", "type": "subnet", "parent": "vault-enclave"},
        ],
        "nodes": [
            {"id": "prod-vm", "label": "Production VM", "service": "Virtual Machine", "group": "prod-enclave"},
            {"id": "prod-files", "label": "File Storage", "service": "File Storage", "group": "prod-enclave"},
            {"id": "prod-bucket", "label": "Operational Bucket", "service": "Object Storage", "group": "prod-enclave"},
            {"id": "orchestrator", "label": "Backup Orchestrator", "service": "Virtual Machine", "group": "ops-subnet"},
            {"id": "worker", "label": "Backup Worker", "service": "Virtual Machine", "group": "ops-subnet"},
            {"id": "immutable-bucket", "label": "Immutable Bucket", "service": "Object Storage", "group": "vault-enclave"},
            {"id": "zdlra", "label": "Zero Data Loss Recovery", "service": "Zero Data Loss Recovery Appliance", "group": "vault-enclave"},
            {"id": "restore-vm", "label": "Clean Room VM", "service": "Virtual Machine", "group": "safe-restore"},
        ],
        "edges": [
            {"from": "prod-vm", "to": "orchestrator", "label": "inventory"},
            {"from": "prod-files", "to": "worker", "label": "backup"},
            {"from": "prod-bucket", "to": "worker", "label": "copy"},
            {"from": "worker", "to": "immutable-bucket", "label": "immutable"},
            {"from": "zdlra", "to": "restore-vm", "label": "validated restore"},
            {"from": "immutable-bucket", "to": "restore-vm", "label": "restore"},
        ],
        "addon_from": "orchestrator",
    },
    {
        "name": "banking-microservices",
        "summary": "microservicios bancarios en OKE con mensajeria y observabilidad",
        "groups": [
            {"id": "region", "label": "OCI Region", "type": "region"},
            {"id": "vcn", "label": "Banking VCN", "type": "vcn", "parent": "region"},
            {"id": "public-subnet", "label": "Public API Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "private-subnet", "label": "Microservices Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "data-subnet", "label": "Core Data Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "ops-subnet", "label": "Operations Subnet", "type": "subnet", "parent": "vcn"},
        ],
        "nodes": [
            {"id": "waf", "label": "WAF", "service": "WAF", "group": "public-subnet"},
            {"id": "api", "label": "API Gateway", "service": "API Gateway", "group": "public-subnet"},
            {"id": "registry", "label": "Container Registry", "service": "OCI Container Registry", "group": "private-subnet"},
            {"id": "oke", "label": "Banking Services", "service": "OKE", "group": "private-subnet"},
            {"id": "streaming", "label": "Event Streaming", "service": "Streaming", "group": "private-subnet"},
            {"id": "queue", "label": "Payment Queue", "service": "OCI Queue", "group": "private-subnet"},
            {"id": "adb", "label": "Transaction Database", "service": "Oracle Autonomous Database", "group": "data-subnet"},
            {"id": "logging-analytics", "label": "Logging Analytics", "service": "Logging Analytics", "group": "ops-subnet"},
        ],
        "edges": [
            {"from": "waf", "to": "api", "label": "HTTPS"},
            {"from": "api", "to": "oke", "label": "REST"},
            {"from": "registry", "to": "oke", "label": "images"},
            {"from": "oke", "to": "streaming", "label": "events"},
            {"from": "oke", "to": "queue", "label": "async"},
            {"from": "oke", "to": "adb", "label": "SQL"},
            {"from": "oke", "to": "logging-analytics", "label": "logs"},
        ],
        "addon_from": "oke",
    },
    {
        "name": "ai-document-processing",
        "summary": "procesamiento de documentos con Functions, Vision y Document Understanding",
        "groups": [
            {"id": "region", "label": "OCI Region", "type": "region"},
            {"id": "vcn", "label": "AI Processing VCN", "type": "vcn", "parent": "region"},
            {"id": "public-subnet", "label": "API Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "private-subnet", "label": "Processing Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "data-subnet", "label": "Data Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "ops-subnet", "label": "Operations Subnet", "type": "subnet", "parent": "vcn"},
        ],
        "nodes": [
            {"id": "api", "label": "Upload API", "service": "API Gateway", "group": "public-subnet"},
            {"id": "functions", "label": "Classifier Function", "service": "Functions", "group": "private-subnet"},
            {"id": "input-bucket", "label": "Input Documents", "service": "Object Storage", "group": "data-subnet"},
            {"id": "doc-understanding", "label": "Document Understanding", "service": "Document Understanding", "group": "private-subnet"},
            {"id": "vision", "label": "Vision OCR", "service": "OCI Vision", "group": "private-subnet"},
            {"id": "data-science", "label": "Model Endpoint", "service": "Data Science", "group": "private-subnet"},
            {"id": "adb", "label": "Result Store", "service": "Oracle Autonomous Database", "group": "data-subnet"},
            {"id": "email", "label": "Email Delivery", "service": "Email Delivery", "group": "ops-subnet"},
        ],
        "edges": [
            {"from": "api", "to": "functions", "label": "invoke"},
            {"from": "functions", "to": "input-bucket", "label": "store"},
            {"from": "input-bucket", "to": "doc-understanding", "label": "extract"},
            {"from": "input-bucket", "to": "vision", "label": "ocr"},
            {"from": "doc-understanding", "to": "data-science", "label": "features"},
            {"from": "data-science", "to": "adb", "label": "persist"},
            {"from": "functions", "to": "email", "label": "notify"},
        ],
        "addon_from": "functions",
    },
    {
        "name": "security-observability",
        "summary": "perimetro seguro con firewall, bastion, logging y monitoreo",
        "groups": [
            {"id": "region", "label": "OCI Region", "type": "region"},
            {"id": "vcn", "label": "Secured VCN", "type": "vcn", "parent": "region"},
            {"id": "public-subnet", "label": "Public Edge Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "private-subnet", "label": "Private Workload Subnet", "type": "subnet", "parent": "vcn"},
            {"id": "ops-subnet", "label": "Security Operations", "type": "subnet", "parent": "vcn"},
        ],
        "nodes": [
            {"id": "dns", "label": "DNS", "service": "DNS", "group": "public-subnet"},
            {"id": "waf", "label": "WAF", "service": "WAF", "group": "public-subnet"},
            {"id": "firewall", "label": "Network Firewall", "service": "Firewall", "group": "public-subnet"},
            {"id": "lb", "label": "Load Balancer", "service": "Load Balancer", "group": "public-subnet"},
            {"id": "workload", "label": "Workload VM", "service": "Virtual Machine", "group": "private-subnet"},
            {"id": "bastion", "label": "Bastion", "service": "Bastion", "group": "ops-subnet"},
            {"id": "logging", "label": "Logging", "service": "Logging", "group": "ops-subnet"},
            {"id": "monitoring", "label": "Monitoring", "service": "Monitoring", "group": "ops-subnet"},
            {"id": "vault", "label": "Vault", "service": "Vault", "group": "ops-subnet"},
        ],
        "edges": [
            {"from": "dns", "to": "waf", "label": "DNS"},
            {"from": "waf", "to": "firewall", "label": "inspect"},
            {"from": "firewall", "to": "lb", "label": "allow"},
            {"from": "lb", "to": "workload", "label": "HTTPS"},
            {"from": "bastion", "to": "workload", "label": "SSH"},
            {"from": "workload", "to": "logging", "label": "logs"},
            {"from": "workload", "to": "monitoring", "label": "metrics"},
            {"from": "workload", "to": "vault", "label": "secrets"},
        ],
        "addon_from": "workload",
    },
]


def ensure_group(spec: dict[str, Any], group_id: str) -> None:
    if any(group["id"] == group_id for group in spec["groups"]):
        return
    parent = "vcn" if any(group["id"] == "vcn" for group in spec["groups"]) else ""
    spec["groups"].append({"id": group_id, "label": "Operations", "type": "subnet", "parent": parent})


def architecture_prompt_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for base in BASE_ARCHITECTURES:
        for index, variant in enumerate(VARIANTS, start=1):
            spec = {
                "title": f"OCI {base['name']} - {variant['theme']}",
                "layout": "left-to-right",
                "groups": copy.deepcopy(base["groups"]),
                "nodes": copy.deepcopy(base["nodes"]),
                "edges": copy.deepcopy(base["edges"]),
            }
            addon_id, addon_label, addon_service, addon_group, edge_label = variant["addon"]
            unique_addon_id = f"{addon_id}-{index}"
            ensure_group(spec, addon_group)
            spec["nodes"].append(
                {
                    "id": unique_addon_id,
                    "label": addon_label,
                    "service": addon_service,
                    "group": addon_group,
                }
            )
            spec["edges"].append(
                {
                    "from": base["addon_from"],
                    "to": unique_addon_id,
                    "label": edge_label,
                }
            )
            prompt = (
                f"Disena una arquitectura OCI de {base['summary']} para {variant['theme']}; "
                f"incluye grupos de red, servicios principales, flujos entre capas y {variant['constraint']}; "
                f"agrega {addon_label} y muestra las conexiones criticas de extremo a extremo."
            )
            cases.append(
                {
                    "id": f"{base['name']}-{index:02d}",
                    "prompt": prompt,
                    "sourcePattern": base["name"],
                    "reference": "Oracle Cloud Architecture Center",
                    "spec": spec,
                }
            )
    return cases
