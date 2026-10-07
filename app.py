"""Sına'nın Streamlit kullanıcı arayüzü."""

import os
from pathlib import Path

import streamlit as st

from sina.workflow import generate_test_workflow, run_test_workflow


def _initialize_session_state() -> None:
    st.session_state.setdefault("generation_result", None)
    st.session_state.setdefault("generation_source_code", None)
    st.session_state.setdefault("generation_target_module", None)
    st.session_state.setdefault("run_result", None)
    st.session_state.setdefault("target_module_input", "")
    st.session_state.setdefault("last_uploaded_filename", None)
    st.session_state.setdefault("last_suggested_target_module", None)


def _safe_error_message(exc: Exception) -> str:
    message = str(exc)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    return f"{type(exc).__name__}: {message}"


def _show_functions(functions: list[object]) -> None:
    st.markdown("### Fonksiyon Analizi")
    for function in functions:
        with st.expander(f"Fonksiyon: {function.name}", expanded=True):
            parameters = ", ".join(function.parameters) or "Yok"
            st.write(f"**Parametreler:** {parameters}")
            st.write(f"**Return var mı?:** {'Evet' if function.has_return else 'Hayır'}")

            st.write("**Koşullar:**")
            if function.conditions:
                st.table(
                    [
                        {
                            "Sol taraf": condition.left,
                            "Operatör": condition.operator,
                            "Sağ taraf": condition.right,
                        }
                        for condition in function.conditions
                    ]
                )
            else:
                st.caption("Sayısal sınır koşulu bulunmadı.")

            st.write("**Exception'lar:**")
            if function.exceptions:
                st.table(
                    [
                        {
                            "Tür": exception.type,
                            "Koşul": exception.condition,
                            "Mesaj": exception.message,
                        }
                        for exception in function.exceptions
                    ]
                )
            else:
                st.caption("Exception bilgisi bulunmadı.")


def _show_scenarios(scenarios: list[object]) -> None:
    st.markdown("### Test Senaryoları")
    st.table(
        [
            {
                "Fonksiyon": scenario.function_name,
                "Tür": scenario.kind,
                "Açıklama": scenario.description,
                "Koşul": scenario.condition,
                "Beklenen exception": scenario.expected_exception,
            }
            for scenario in scenarios
        ]
    )


def _show_run_result(result: object) -> None:
    status_messages = {
        "passed": (st.success, "Testler başarıyla geçti."),
        "failed": (st.error, "Testlerden en az biri başarısız oldu."),
        "error": (st.error, "Pytest çalıştırılırken bir hata oluştu."),
        "timeout": (st.warning, "Test çalıştırma zaman aşımına uğradı."),
    }
    message_function, message = status_messages.get(
        result.status,
        (st.info, f"Bilinmeyen sonuç durumu: {result.status}"),
    )
    message_function(message)
    st.caption(f"Return code: {result.return_code}")

    with st.expander("Pytest çıktısını göster"):
        st.code(result.stdout or "(stdout boş)", language="text")

    if result.stderr:
        with st.expander("Hata çıktısını göster"):
            st.code(result.stderr, language="text")


def main() -> None:
    st.set_page_config(page_title="Sına", page_icon="🧪", layout="wide")
    _initialize_session_state()

    st.title("Sına")
    st.write(
        "Python kodunu analiz eder, test senaryoları oluşturur ve "
        "AI destekli pytest testleri üretir."
    )

    st.subheader("1. Kodunu Gir")
    uploaded_file = st.file_uploader("Python dosyası yükle", type=["py"])
    pasted_source_code = st.text_area(
        "Python kodunu yapıştır",
        height=300,
        placeholder="def topla(a, b):\n    return a + b",
    )
    st.caption(
        "Dosya yüklerseniz UTF-8 dosya içeriği öncelikli kullanılır."
    )

    source_code = pasted_source_code
    file_read_error: UnicodeDecodeError | None = None
    if uploaded_file is not None:
        try:
            source_code = uploaded_file.getvalue().decode("utf-8")
            st.info(f"Aktif kaynak: {uploaded_file.name}")
        except UnicodeDecodeError as exc:
            source_code = ""
            file_read_error = exc
            st.error("Yüklenen dosya UTF-8 olarak okunamadı.")

    uploaded_filename = uploaded_file.name if uploaded_file is not None else None
    if uploaded_filename != st.session_state["last_uploaded_filename"]:
        previous_suggestion = st.session_state["last_suggested_target_module"]
        if uploaded_filename is not None:
            suggested_target_module = Path(uploaded_filename).stem
            st.session_state["target_module_input"] = suggested_target_module
            st.session_state["last_suggested_target_module"] = suggested_target_module
        else:
            if st.session_state["target_module_input"] == previous_suggestion:
                st.session_state["target_module_input"] = ""
            st.session_state["last_suggested_target_module"] = None
        st.session_state["last_uploaded_filename"] = uploaded_filename

    target_module = st.text_input(
        "Target module",
        key="target_module_input",
        placeholder="calculator",
        help="Örnek: calculator.py → calculator",
    )

    if st.button("Test Üret", type="primary", disabled=file_read_error is not None):
        st.session_state["run_result"] = None
        try:
            with st.spinner("Testler üretiliyor..."):
                generation_result = generate_test_workflow(
                    source_code,
                    target_module,
                )
        except Exception as exc:
            st.error(f"Test üretilemedi: {_safe_error_message(exc)}")
        else:
            st.session_state["generation_result"] = generation_result
            st.session_state["generation_source_code"] = source_code
            st.session_state["generation_target_module"] = target_module
            st.success("Test kodu üretildi ve statik doğrulamadan geçti.")

    generation_result = st.session_state["generation_result"]
    is_stale = generation_result is not None and (
        source_code != st.session_state["generation_source_code"]
        or target_module != st.session_state["generation_target_module"]
    )
    if generation_result is not None:
        st.divider()
        st.subheader("2. Analiz ve Test Senaryoları")
        _show_functions(generation_result.functions)
        _show_scenarios(generation_result.scenarios)

        st.divider()
        st.subheader("3. Üretilen Pytest Kodu")
        if is_stale:
            st.warning(
                "Kaynak kod veya target module değişti. Gösterilen testler eski "
                "girdilere ait. Testleri yeniden üretin."
            )
        st.code(generation_result.generated_test_code, language="python")
        download_module_name = "".join(
            character if character.isalnum() or character == "_" else "_"
            for character in st.session_state["generation_target_module"]
        )
        download_column, run_column = st.columns(2)
        with download_column:
            st.download_button(
                "Test Dosyasını İndir",
                data=generation_result.generated_test_code.encode("utf-8"),
                file_name=f"test_{download_module_name}.py",
                mime="text/x-python",
                disabled=is_stale,
                on_click="ignore",
            )
            st.caption(
                "İndirilen dosyayı projenizde tests/ klasörüne ekleyip "
                "pytest ile çalıştırabilirsiniz."
            )
        with run_column:
            st.warning(
                "Testler ayrı subprocess içinde çalıştırılır; runner tam bir "
                "sandbox değildir. Network ve dosya sistemi erişimi izole edilmez."
            )
            can_run = not is_stale
            if st.button("Testleri Çalıştır", disabled=not can_run) and can_run:
                st.session_state["run_result"] = None
                try:
                    with st.spinner("Pytest çalıştırılıyor..."):
                        run_result = run_test_workflow(
                            st.session_state["generation_source_code"],
                            generation_result.generated_test_code,
                            st.session_state["generation_target_module"],
                        )
                except Exception as exc:
                    st.error(f"Testler çalıştırılamadı: {_safe_error_message(exc)}")
                else:
                    st.session_state["run_result"] = run_result

    run_result = st.session_state["run_result"]
    if run_result is not None and not is_stale:
        st.divider()
        st.subheader("4. Test Sonucu")
        _show_run_result(run_result)


if __name__ == "__main__":
    main()
