from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main as pipeline_main  # noqa: E402

from config import CLEAN_DATA_DIR, EXPORT_DIR, RAW_DATA_DIR, ensure_directories  # noqa: E402
from ozon.export_xlsx import export_to_xlsx  # noqa: E402
from translator.ai_hashtag_service import generate_hashtags  # noqa: E402
from translator.ai_translator import translate_product_fields  # noqa: E402

from ..schemas.crawl_schema import CrawlRequest
from .runtime_store import runtime_store


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_name(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in text).strip("_") or "export"


def _resolve_input(request: CrawlRequest) -> tuple[str, str]:
    if request.product_url:
        return request.product_url.strip(), pipeline_main.SOURCE_MODE_PRODUCT_URL
    if request.shop_url:
        return request.shop_url.strip(), pipeline_main.SOURCE_MODE_SHOP_URL
    if request.keyword:
        return request.keyword.strip(), pipeline_main.SOURCE_MODE_KEYWORD
    raise ValueError("One of keyword, product_url, or shop_url is required.")


def _resolve_mode(request: CrawlRequest) -> str:
    if request.options.input_mode:
        return str(request.options.input_mode)
    if request.product_url:
        return "product_url"
    if request.shop_url:
        return "shop_url"
    return "keyword"


def _build_result_item(
    *,
    index: int,
    source: str,
    source_value: str,
    raw_path: Path,
    clean_path: Path,
    raw_product: dict[str, Any],
    normalized_product: dict[str, Any],
    mapped_product: dict[str, Any] | None,
    translated: bool,
) -> dict[str, Any]:
    mapped_price = ""
    if mapped_product is not None:
        mapped_price = str(mapped_product.get("row_data", {}).get("Price, CNY*", "") or "")
    price = str(raw_product.get("price") or normalized_product.get("price") or mapped_price)
    sku = ""
    if mapped_product:
        sku = str(mapped_product.get("row_data", {}).get("Article code*", "") or "")
    if not sku:
        sku = str(raw_product.get("sku") or raw_product.get("product_sku") or f"ITEM-{index:03d}")

    name = str(
        normalized_product.get("translated_title")
        or normalized_product.get("title")
        or raw_product.get("title")
        or raw_product.get("product_name")
        or f"Product {index}"
    )
    return {
        "id": f"item-{index:03d}",
        "source": source,
        "name": name,
        "sku": sku,
        "price": price,
        "status": "success",
        "mapping": 100 if mapped_product is not None else 0,
        "translation": 100 if translated else 0,
        "exported": False,
        "updated_at": _timestamp(),
        "product_count": 1,
        "product_url": source_value,
        "raw_file_path": str(raw_path),
        "normalized_file_path": str(clean_path),
        "raw_product": raw_product,
        "normalized_product": normalized_product,
        "mapped_product": mapped_product,
    }


def _process_raw_product(
    *,
    job_id: str,
    index: int,
    source: str,
    source_value: str,
    raw_product: dict[str, Any],
    translate_enabled: bool,
    map_enabled: bool,
    generate_hashtags_enabled: bool,
) -> dict[str, Any]:
    raw_path = RAW_DATA_DIR / f"{job_id}_product_{index:03d}.json"
    pipeline_main.save_json_with_fallback(raw_product, raw_path)

    normalized_product = pipeline_main.normalize_product(raw_product)
    if translate_enabled:
        normalized_product = translate_product_fields(normalized_product)
    if generate_hashtags_enabled:
        normalized_product = generate_hashtags(normalized_product)

    clean_path = CLEAN_DATA_DIR / f"{job_id}_product_{index:03d}.json"
    pipeline_main.save_json_with_fallback(normalized_product, clean_path)

    mapped_product = pipeline_main.map_to_ozon_product(normalized_product) if map_enabled else None
    return _build_result_item(
        index=index,
        source=source,
        source_value=source_value,
        raw_path=raw_path,
        clean_path=clean_path,
        raw_product=raw_product,
        normalized_product=normalized_product,
        mapped_product=mapped_product,
        translated=translate_enabled,
    )


def _run_sync_crawl(job_id: str, request: CrawlRequest) -> dict[str, Any]:
    ensure_directories()
    source = str(request.platform or "").strip().lower()
    source_value, source_mode = _resolve_input(request)
    options = request.options

    translate_enabled = bool(options.translate_to_russian)
    map_enabled = bool(options.map_to_ozon)
    export_enabled = bool(options.export_excel)
    generate_hashtags_enabled = bool(options.generate_hashtags)
    max_links = int(options.max_links)

    runtime_store.update_job(
        job_id,
        status="running",
        message="Preparing crawl pipeline",
        total=0,
        processed=0,
        progress={"stage": "prepare", "processed": 0, "total": 0},
    )

    items: list[dict[str, Any]] = []
    page = None
    browser = None
    context = None
    playwright = None

    try:
        if pipeline_main.is_zyte_source(source):
            runtime_store.update_job(
                job_id,
                status="running",
                message="Crawling source product",
                total=1,
                processed=0,
                progress={"stage": "crawl", "processed": 0, "total": 1},
                result={
                    "summary": {
                        "platform": source,
                        "input_mode": source_mode,
                        "requested_input": source_value,
                        "total_items": 1,
                        "success_count": 0,
                        "failed_count": 0,
                    },
                    "items": items,
                    "export": None,
                },
            )
            raw_product = pipeline_main.crawl_product_detail(
                page=None,  # type: ignore[arg-type]
                product_link=source_value,
                source=source,
                crawl_hint=source_value,
            )
            runtime_store.update_job(
                job_id,
                status="running",
                message="Normalizing product data",
                total=1,
                processed=0,
                progress={"stage": "clean", "processed": 0, "total": 1},
            )
            items.append(
                _process_raw_product(
                    job_id=job_id,
                    index=1,
                    source=source,
                    source_value=source_value,
                    raw_product=raw_product,
                    translate_enabled=translate_enabled,
                    map_enabled=map_enabled,
                    generate_hashtags_enabled=generate_hashtags_enabled,
                )
            )
            runtime_store.update_job(
                job_id,
                status="running",
                message="Processed product 1/1",
                total=1,
                processed=1,
                success=1,
                failed=0,
                progress={"stage": "map", "processed": 1, "total": 1},
                result={
                    "summary": {
                        "platform": source,
                        "input_mode": source_mode,
                        "requested_input": source_value,
                        "total_items": 1,
                        "success_count": 1,
                        "failed_count": 0,
                    },
                    "items": items,
                    "export": None,
                },
            )
        else:
            playwright, browser, context, page = pipeline_main.create_browser_page(source=source)
            product_links = pipeline_main.resolve_product_links(
                page=page,
                source_value=source_value,
                source_mode=source_mode,
                max_links=max_links,
            )
            runtime_store.update_job(
                job_id,
                status="running",
                message="Collected product links",
                total=len(product_links),
                processed=0,
                progress={
                    "stage": "crawl",
                    "processed": 0,
                    "total": len(product_links),
                },
            )
            for index, product_link in enumerate(product_links, start=1):
                runtime_store.update_job(
                    job_id,
                    status="running",
                    message=f"Crawling product {index}/{len(product_links)}",
                    total=len(product_links),
                    processed=index - 1,
                    progress={
                        "stage": "crawl",
                        "processed": index - 1,
                        "total": len(product_links),
                    },
                )
                raw_product = pipeline_main.crawl_product_detail(
                    page=page,
                    product_link=product_link,
                    source=source,
                    crawl_hint=source_value,
                )
                runtime_store.update_job(
                    job_id,
                    status="running",
                    message=f"Cleaning product {index}/{len(product_links)}",
                    total=len(product_links),
                    processed=index - 1,
                    progress={
                        "stage": "clean",
                        "processed": index - 1,
                        "total": len(product_links),
                    },
                )
                items.append(
                    _process_raw_product(
                        job_id=job_id,
                        index=index,
                        source=source,
                        source_value=product_link,
                        raw_product=raw_product,
                        translate_enabled=translate_enabled,
                        map_enabled=map_enabled,
                        generate_hashtags_enabled=generate_hashtags_enabled,
                    )
                )
                stage = "map" if map_enabled else "translate" if translate_enabled else "clean"
                runtime_store.update_job(
                    job_id,
                    status="running",
                    message=f"Processed product {index}/{len(product_links)}",
                    total=len(product_links),
                    processed=index,
                    success=len(items),
                    failed=0,
                    progress={
                        "stage": stage,
                        "processed": index,
                        "total": len(product_links),
                    },
                    result={
                        "summary": {
                            "platform": source,
                            "input_mode": source_mode,
                            "requested_input": source_value,
                            "total_items": len(product_links),
                            "success_count": len(items),
                            "failed_count": 0,
                        },
                        "items": items,
                        "export": None,
                    },
                )

        export_payload: dict[str, Any] | None = None
        if export_enabled and items:
            runtime_store.update_job(
                job_id,
                status="running",
                message="Exporting Excel file",
                total=len(items),
                processed=len(items),
                success=len(items),
                failed=0,
                progress={
                    "stage": "export",
                    "processed": len(items),
                    "total": len(items),
                },
                result={
                    "summary": {
                        "platform": source,
                        "input_mode": source_mode,
                        "requested_input": source_value,
                        "total_items": len(items),
                        "success_count": len(items),
                        "failed_count": 0,
                    },
                    "items": items,
                    "export": None,
                },
            )
            mapped_products = [
                item["mapped_product"]
                for item in items
                if isinstance(item.get("mapped_product"), dict)
            ]
            if mapped_products:
                export_file_name = f"{_safe_name(job_id)}_{_safe_name(source)}.xlsx"
                export_path = EXPORT_DIR / export_file_name
                export_to_xlsx(mapped_products, str(export_path))
                file_id, file_path = runtime_store.register_file(export_path)
                export_payload = {
                    "file_id": file_id,
                    "file_name": file_path.name,
                    "download_url": f"/download/{file_id}",
                }
                for item in items:
                    item["exported"] = True

        return {
            "summary": {
                "platform": source,
                "input_mode": source_mode,
                "requested_input": source_value,
                "total_items": len(items),
                "success_count": len(items),
                "failed_count": 0,
            },
            "items": items,
            "export": export_payload,
        }
    finally:
        if page is not None:
            page.close()
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()
        if playwright is not None:
            playwright.stop()


def _crawl_job_runner(job_id: str, request: CrawlRequest) -> None:
    try:
        result = _run_sync_crawl(job_id, request)
        runtime_store.update_job(
            job_id,
            status="success",
            message="Crawl completed",
            total=result["summary"]["total_items"],
            processed=result["summary"]["total_items"],
            success=result["summary"]["success_count"],
            failed=result["summary"]["failed_count"],
            progress={
                "stage": "done",
                "processed": result["summary"]["success_count"],
                "total": result["summary"]["total_items"],
            },
            result=result,
        )
    except Exception as exc:
        runtime_store.update_job(
            job_id,
            status="failed",
            message="Crawl failed",
            error=str(exc),
        )


def submit_crawl_job(request: CrawlRequest) -> dict[str, Any]:
    record = runtime_store.create_job(
        message="Crawl job submitted",
        source=str(request.platform or "").strip(),
        mode=_resolve_mode(request),
    )
    worker = Thread(
        target=_crawl_job_runner,
        args=(record.job_id, request),
        daemon=True,
    )
    worker.start()
    return record.to_dict()


def get_job_status(job_id: str) -> dict[str, Any] | None:
    record = runtime_store.get_job(job_id)
    return record.to_dict() if record else None


def get_job_result(job_id: str) -> dict[str, Any] | None:
    record = runtime_store.get_job(job_id)
    if record is None:
        return None
    return {
        "job_id": record.job_id,
        "status": record.status,
        "result": record.result,
        "error": record.error,
    }
