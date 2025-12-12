"""
EDAP Streamlit Web UI.

Run with: streamlit run edap/ui.py
"""

import io
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Optional

from edap import (
    PatternAnalyzer,
    RandomGenerator,
    SmartGenerator,
    PatternGenerator,
    RegexGenerator,
    RegexInferenceGenerator,
    MarkovGenerator,
    HybridGenerator,
    create_hybrid_generator,
    RegexBuilder,
    Hasher,
    HashAlgorithm,
    ResultExporter,
    OutputFormat,
    Mutator,
    RULE_PRESETS,
    Scorer,
    Filter,
    FilterConfig,
    create_filter,
    FILTER_PRESETS,
    StatsExporter,
)


# Page config
st.set_page_config(
    page_title="EDAP - Pattern Analysis & Generation",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-top: 0;
    }
    .stat-box {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
    }
    .generated-word {
        font-family: monospace;
        background-color: #e8f4ea;
        padding: 2px 6px;
        border-radius: 3px;
        margin: 2px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'generated_words' not in st.session_state:
        st.session_state.generated_words = []
    if 'input_words' not in st.session_state:
        st.session_state.input_words = []
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = None
    if 'last_input_hash' not in st.session_state:
        st.session_state.last_input_hash = None


def clear_analysis():
    """Clear analysis when input changes."""
    st.session_state.analysis_result = None
    st.session_state.generated_words = []
    st.session_state.analyzer = None


def render_header():
    """Render the header section."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<p class="main-header">EDAP</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Empirical Distribution Analysis for Patterns</p>', unsafe_allow_html=True)
    with col2:
        st.markdown("**Author:** Ehab Hussein")
        st.markdown("**Version:** 2.1.0")


def render_sidebar():
    """Render the sidebar with input options."""
    st.sidebar.header("📥 Input")

    input_method = st.sidebar.radio(
        "Input Method",
        ["Upload File", "Paste Text", "Sample Data"],
        help="Choose how to provide your wordlist"
    )

    words = []

    if input_method == "Upload File":
        uploaded_file = st.sidebar.file_uploader(
            "Upload wordlist",
            type=['txt', 'csv', 'lst'],
            help="One word per line"
        )
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8', errors='ignore')
            words = [w.strip() for w in content.splitlines() if w.strip()]
            st.sidebar.success(f"Loaded {len(words)} words")

    elif input_method == "Paste Text":
        text_input = st.sidebar.text_area(
            "Paste words (one per line)",
            height=200,
            placeholder="password123\nAdmin2024\nuser@123\n..."
        )
        if text_input:
            words = [w.strip() for w in text_input.splitlines() if w.strip()]
            st.sidebar.info(f"Found {len(words)} words")

    else:  # Sample Data
        sample_type = st.sidebar.selectbox(
            "Sample Type",
            ["Passwords", "Usernames", "UUIDs", "Hashes (MD5-like)"]
        )

        samples = {
            "Passwords": [
                "Password123!", "Admin@2024", "Welcome1", "Qwerty123",
                "Summer2024!", "Winter@123", "Spring2023", "Fall2024!",
                "User123!", "Guest@456", "Test1234", "Demo@2024",
                "Hello123!", "World@456", "Python123", "Code@2024",
            ],
            "Usernames": [
                "john_doe", "jane_smith", "admin_user", "guest_123",
                "user_2024", "test_account", "demo_user", "new_member",
                "super_admin", "power_user", "basic_user", "temp_access",
            ],
            "UUIDs": [
                "550e8400-e29b-41d4-a716-446655440000",
                "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
                "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            ],
            "Hashes (MD5-like)": [
                "5d41402abc4b2a76b9719d911017c592",
                "098f6bcd4621d373cade4e832627b4f6",
                "d8578edf8458ce06fbc5bb76a58c5ca4",
                "25d55ad283aa400af464c76d713c07ad",
                "e99a18c428cb38d5f260853678922e03",
            ],
        }

        words = samples[sample_type]
        st.sidebar.info(f"Using {len(words)} sample {sample_type.lower()}")

    # Detect input changes and clear stale analysis
    current_input_hash = hash(tuple(words)) if words else None
    if current_input_hash != st.session_state.last_input_hash:
        if st.session_state.last_input_hash is not None:
            # Input changed, clear old analysis
            clear_analysis()
        st.session_state.last_input_hash = current_input_hash

    st.sidebar.divider()

    # Analysis options
    st.sidebar.header("🔧 Analysis Options")

    min_length = st.sidebar.number_input(
        "Min word length",
        min_value=1,
        max_value=100,
        value=1,
    )

    max_length = st.sidebar.number_input(
        "Max word length",
        min_value=1,
        max_value=500,
        value=256,
    )

    return words, min_length, max_length


def render_generation_options():
    """Render generation options in the main area."""
    st.subheader("🎲 Generation Options")

    col1, col2, col3 = st.columns(3)

    with col1:
        mode = st.selectbox(
            "Generation Mode",
            ["smart", "random", "pattern", "regex", "markov", "hybrid"],
            help="""
            - **smart**: Uses character co-occurrence patterns
            - **random**: Random selection from position charset
            - **pattern**: Follows character type patterns (Upper/lower/digit/symbol)
            - **regex**: Generate from custom regex pattern
            - **markov**: Uses n-gram transitions (learns sequences)
            - **hybrid**: Combines multiple generators
            """
        )

    with col2:
        count = st.number_input(
            "Number to generate",
            min_value=1,
            max_value=10000,
            value=100,
        )

    with col3:
        seed = st.number_input(
            "Random seed (0 = random)",
            min_value=0,
            max_value=999999,
            value=0,
            help="Set a seed for reproducible results"
        )

    # Mode-specific options
    regex_pattern = None
    type_pattern = None

    if mode == "regex":
        regex_pattern = st.text_input(
            "Regex Pattern",
            value=r"[A-Z][a-z]{3}[0-9]{2}",
            help="Regular expression pattern to match"
        )

        st.caption("Examples: `[A-Z][a-z]{3}[0-9]{2}`, `(user|admin)[0-9]{3}`, `[a-f0-9]{8}-[a-f0-9]{4}`")

    elif mode == "pattern":
        type_pattern = st.text_input(
            "Type Pattern (optional)",
            placeholder="e.g., Ullnn@ for Upper-lower-lower-digit-digit-symbol",
            help="U=Upper, l=lower, n=digit, @=symbol. Leave empty to auto-select."
        )

    elif mode == "markov":
        markov_order = st.slider(
            "Markov Order (n-gram size)",
            min_value=1,
            max_value=4,
            value=2,
            help="Higher = more similar to training data, lower = more random"
        )

    elif mode == "hybrid":
        hybrid_mode = st.selectbox(
            "Hybrid Preset",
            ["balanced", "strict", "creative"],
            help="""
            - **balanced**: 50% smart + 30% pattern + 20% random
            - **strict**: 70% pattern + 30% smart
            - **creative**: 50% random + 30% smart + 20% pattern
            """
        )

    # Advanced options
    with st.expander("Advanced Options"):
        col1, col2 = st.columns(2)

        with col1:
            allow_duplicates = st.checkbox(
                "Allow duplicates from input",
                value=False,
                help="If checked, generated words may include original input words"
            )

        with col2:
            use_learned = st.checkbox(
                "Prefer learned charset (regex mode)",
                value=True,
                help="For regex mode: prefer characters seen in training data"
            )

    return {
        'mode': mode,
        'count': count,
        'seed': seed if seed > 0 else None,
        'regex_pattern': regex_pattern,
        'type_pattern': type_pattern if type_pattern else None,
        'allow_duplicates': allow_duplicates,
        'use_learned': use_learned,
        'markov_order': markov_order if mode == 'markov' else 2,
        'hybrid_mode': hybrid_mode if mode == 'hybrid' else 'balanced',
    }


def render_export_options():
    """Render export options."""
    st.subheader("📤 Export Options")

    col1, col2 = st.columns(2)

    with col1:
        output_format = st.selectbox(
            "Output Format",
            ["text", "json", "csv", "jsonl"],
        )

    with col2:
        hash_algo = st.selectbox(
            "Apply Hash (optional)",
            ["None"] + HashAlgorithm.list_algorithms(),
        )

    return {
        'format': output_format,
        'hash': hash_algo if hash_algo != "None" else None,
    }


def run_analysis(words: list, min_length: int, max_length: int):
    """Run pattern analysis on the words."""
    analyzer = PatternAnalyzer(min_length=min_length, max_length=max_length)
    result = analyzer.analyze_words(words)

    st.session_state.analyzer = analyzer
    st.session_state.analysis_result = result
    st.session_state.input_words = words

    return result


def run_generation(result, options: dict) -> list:
    """Generate new strings based on analysis and options."""
    mode = options['mode']
    seed = options['seed']
    exclude_original = not options['allow_duplicates']

    if mode == 'random':
        gen = RandomGenerator(result, seed=seed, exclude_original=exclude_original)
    elif mode == 'smart':
        gen = SmartGenerator(result, seed=seed, exclude_original=exclude_original)
    elif mode == 'pattern':
        gen = PatternGenerator(result, seed=seed, exclude_original=exclude_original)
    elif mode == 'regex':
        gen = RegexGenerator(
            result,
            pattern=options['regex_pattern'],
            seed=seed,
            exclude_original=exclude_original,
            use_learned_charset=options['use_learned'],
        )
    elif mode == 'markov':
        gen = MarkovGenerator(
            result,
            seed=seed,
            exclude_original=exclude_original,
            order=options.get('markov_order', 2),
        )
        # Train on original words for better Markov chains
        gen.train_on_words(st.session_state.input_words)
    elif mode == 'hybrid':
        gen = create_hybrid_generator(
            result,
            mode=options.get('hybrid_mode', 'balanced'),
            seed=seed,
            exclude_original=exclude_original,
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Set original words for exclusion
    gen.set_original_words(set(st.session_state.input_words))

    # Handle explicit pattern for pattern mode
    if mode == 'pattern' and options.get('type_pattern'):
        generated = []
        for _ in range(options['count']):
            word = gen.generate_from_explicit_pattern(options['type_pattern'])
            if word:
                generated.append(word)
        return generated

    return gen.generate(options['count'])


def render_analysis_results(result):
    """Render analysis results."""
    st.subheader("📊 Analysis Results")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Words", result.total_words)
    with col2:
        st.metric("Unique Words", result.unique_words)
    with col3:
        st.metric("Min Length", result.min_length)
    with col4:
        st.metric("Max Length", result.max_length)

    # Tabs for detailed info
    tab1, tab2, tab3, tab4 = st.tabs(["Length Distribution", "Character Types", "Charset", "Patterns"])

    with tab1:
        if result.length_stats:
            length_data = {
                'Length': [],
                'Count': [],
                'Percentage': [],
            }
            total = sum(ls.count for ls in result.length_stats.values())

            for length in sorted(result.length_stats.keys()):
                ls = result.length_stats[length]
                length_data['Length'].append(length)
                length_data['Count'].append(ls.count)
                length_data['Percentage'].append(f"{ls.count/total*100:.1f}%")

            df = pd.DataFrame(length_data)

            col1, col2 = st.columns([2, 1])
            with col1:
                st.bar_chart(df.set_index('Length')['Count'])
            with col2:
                st.dataframe(df, hide_index=True)

    with tab2:
        type_data = []
        total_chars = sum(result.global_type_frequency.values())

        from edap.models import CharType
        for ct in CharType:
            count = result.global_type_frequency.get(ct, 0)
            pct = count / total_chars * 100 if total_chars > 0 else 0
            type_data.append({
                'Type': ct.name,
                'Symbol': ct.value,
                'Count': count,
                'Percentage': f"{pct:.1f}%"
            })

        st.dataframe(pd.DataFrame(type_data), hide_index=True)

    with tab3:
        st.text(f"Charset ({len(result.charset)} chars):")
        st.code(''.join(sorted(result.charset)))

        if result.discarded_charset:
            st.text(f"Unused keyboard chars ({len(result.discarded_charset)}):")
            st.code(''.join(sorted(result.discarded_charset)))

    with tab4:
        # Show inferred patterns
        patterns_data = []
        for length in sorted(result.length_stats.keys())[:10]:  # Top 10 lengths
            ls = result.length_stats[length]
            for pattern, count in ls.get_common_patterns(3):
                patterns_data.append({
                    'Length': length,
                    'Pattern': pattern,
                    'Count': count,
                })

        if patterns_data:
            st.dataframe(pd.DataFrame(patterns_data), hide_index=True)
        else:
            st.info("No patterns found")


def render_mutation_options():
    """Render mutation options."""
    st.subheader("🔄 Mutation Options")

    col1, col2 = st.columns(2)

    with col1:
        enable_mutations = st.checkbox(
            "Apply mutations to generated words",
            value=False,
            help="Apply hashcat-style rule transformations"
        )

    with col2:
        mutation_preset = st.selectbox(
            "Mutation Preset",
            ["basic", "leet", "common", "full", "custom"],
            disabled=not enable_mutations,
            help="""
            - **basic**: lowercase, uppercase, capitalize, reverse
            - **leet**: leetspeak transformations
            - **common**: common number/symbol appends
            - **full**: all available rules
            - **custom**: select individual rules
            """
        )

    custom_rules = []
    if enable_mutations and mutation_preset == "custom":
        mutator = Mutator()
        all_rules = mutator.list_rules()
        custom_rules = st.multiselect(
            "Select rules to apply",
            options=all_rules,
            default=["lowercase", "uppercase", "capitalize"],
        )

    return {
        'enabled': enable_mutations,
        'preset': mutation_preset,
        'custom_rules': custom_rules,
    }


def render_filter_options():
    """Render filter options for generated words."""
    st.subheader("🔍 Filter Options")

    col1, col2 = st.columns(2)

    with col1:
        enable_filter = st.checkbox(
            "Filter generated words",
            value=False,
            help="Apply filters to generated output"
        )

    with col2:
        filter_preset = st.selectbox(
            "Filter Preset",
            ["none", "strong", "complex", "custom"],
            disabled=not enable_filter,
            help="""
            - **none**: No filtering
            - **strong**: min 12 chars, 3 char types, score >= 60
            - **complex**: min 16 chars, all char types, score >= 80
            - **custom**: Configure your own filters
            """
        )

    filter_config = {}
    if enable_filter and filter_preset == "custom":
        with st.expander("Custom Filter Settings", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                filter_config['min_length'] = st.number_input(
                    "Min Length", min_value=0, max_value=256, value=8
                )
                filter_config['max_length'] = st.number_input(
                    "Max Length", min_value=0, max_value=256, value=0,
                    help="0 = no limit"
                )

            with col2:
                filter_config['require_upper'] = st.checkbox("Require uppercase")
                filter_config['require_lower'] = st.checkbox("Require lowercase")
                filter_config['require_digit'] = st.checkbox("Require digit")
                filter_config['require_symbol'] = st.checkbox("Require symbol")

            with col3:
                filter_config['min_score'] = st.slider(
                    "Min Strength Score", 0, 100, 0,
                    help="Minimum password strength score"
                )
                filter_config['min_char_types'] = st.slider(
                    "Min Char Types", 1, 4, 1,
                    help="Minimum different character types"
                )

    return {
        'enabled': enable_filter,
        'preset': filter_preset,
        'config': filter_config,
    }


def apply_mutations(words: list, mutation_options: dict) -> list:
    """Apply mutations to generated words."""
    if not mutation_options['enabled']:
        return words

    mutator = Mutator()
    preset = mutation_options['preset']

    if preset == "custom":
        rules = mutation_options['custom_rules']
    elif preset in RULE_PRESETS:
        rules = RULE_PRESETS[preset]
    else:
        rules = RULE_PRESETS.get('basic', [])

    # Expand each word with the selected rules
    mutated = set()
    for word in words:
        mutated.add(word)  # Keep original
        for variant in mutator.expand(word, rules=rules):
            mutated.add(variant)

    return list(mutated)


def apply_filters(words: list, filter_options: dict) -> list:
    """Apply filters to generated words."""
    if not filter_options['enabled']:
        return words

    preset = filter_options['preset']

    if preset == "none":
        return words
    elif preset == "custom":
        config = filter_options['config']
        f = create_filter(
            min_length=config.get('min_length', 0) or None,
            max_length=config.get('max_length', 0) or None,
            require_upper=config.get('require_upper', False),
            require_lower=config.get('require_lower', False),
            require_digit=config.get('require_digit', False),
            require_symbol=config.get('require_symbol', False),
            min_score=config.get('min_score', 0) or None,
            min_char_types=config.get('min_char_types', 1),
        )
    elif preset in FILTER_PRESETS:
        f = Filter(FILTER_PRESETS[preset])
    else:
        return words

    return f.filter(words)


def render_generated_results(words: list, gen_options: dict, export_options: dict,
                             mutation_options: dict = None, filter_options: dict = None):
    """Render generated results."""
    st.subheader(f"✨ Generated Strings ({len(words)})")

    if not words:
        st.warning("No strings generated. Try adjusting your options.")
        return

    # Apply mutations if enabled
    if mutation_options and mutation_options.get('enabled'):
        original_count = len(words)
        words = apply_mutations(words, mutation_options)
        st.info(f"Mutations applied: {original_count} → {len(words)} words")

    # Apply filters if enabled
    if filter_options and filter_options.get('enabled'):
        pre_filter_count = len(words)
        words = apply_filters(words, filter_options)
        st.info(f"Filtered: {pre_filter_count} → {len(words)} words")

    # Display options
    display_mode = st.radio(
        "Display Mode",
        ["Grid", "List", "Table", "Scored Table"],
        horizontal=True,
    )

    if display_mode == "Grid":
        # Grid display
        cols = st.columns(5)
        for i, word in enumerate(words[:500]):  # Limit display
            with cols[i % 5]:
                st.code(word)

    elif display_mode == "List":
        # Simple list
        st.text_area(
            "Generated words",
            value='\n'.join(words[:1000]),
            height=300,
        )

    elif display_mode == "Table":
        # Table with weights
        if st.session_state.analysis_result:
            result = st.session_state.analysis_result
            gen = SmartGenerator(result)  # Just for weight calculation

            table_data = []
            for word in words[:500]:
                weight = gen.calculate_weight(word)
                table_data.append({
                    'Word': word,
                    'Length': len(word),
                    'Weight': weight,
                })

            df = pd.DataFrame(table_data)
            st.dataframe(df, hide_index=True)

    else:  # Scored Table
        # Table with password strength scores
        scorer = Scorer()
        table_data = []

        for word in words[:500]:
            score_result = scorer.score(word)
            table_data.append({
                'Word': word,
                'Length': len(word),
                'Score': round(score_result.score, 1),
                'Rating': score_result.rating,
                'Entropy': round(score_result.entropy, 1),
                'Upper': '✓' if score_result.has_upper else '',
                'Lower': '✓' if score_result.has_lower else '',
                'Digit': '✓' if score_result.has_digit else '',
                'Symbol': '✓' if score_result.has_symbol else '',
            })

        df = pd.DataFrame(table_data)

        # Color-code by rating
        st.dataframe(df, hide_index=True)

        # Show score distribution
        if len(table_data) > 1:
            avg_score = sum(d['Score'] for d in table_data) / len(table_data)
            st.metric("Average Strength Score", f"{avg_score:.1f}/100")

    # Export section
    st.divider()
    st.subheader("💾 Download")

    # Prepare export
    hash_algo = export_options.get('hash')
    output_format = export_options.get('format', 'text')

    # Apply hash if selected
    export_words = words
    if hash_algo:
        hasher = Hasher(hash_algo)
        export_words = hasher.hash_many(words)

    # Format output
    exporter = ResultExporter(format=output_format)
    output_content = exporter.export(export_words, apply_hash=False)  # Already hashed above

    # Determine file extension
    ext_map = {'text': 'txt', 'json': 'json', 'csv': 'csv', 'jsonl': 'jsonl'}
    extension = ext_map.get(output_format, 'txt')

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label=f"📥 Download as {extension.upper()}",
            data=output_content,
            file_name=f"edap_generated.{extension}",
            mime="text/plain",
        )

    with col2:
        if hash_algo:
            st.info(f"Output hashed with {hash_algo.upper()}")


def render_stats_export(result):
    """Render statistics export section."""
    st.subheader("📈 Export Statistics")

    exporter = StatsExporter(result)

    col1, col2, col3 = st.columns(3)

    with col1:
        # JSON export
        json_data = exporter.to_json()
        st.download_button(
            "📥 Download JSON",
            data=json_data,
            file_name="edap_stats.json",
            mime="application/json",
        )

    with col2:
        # CSV export
        csv_data = exporter.to_csv()
        st.download_button(
            "📥 Download CSV",
            data=csv_data,
            file_name="edap_stats.csv",
            mime="text/csv",
        )

    with col3:
        # Position CSV export
        pos_csv = exporter.to_position_csv()
        st.download_button(
            "📥 Download Position CSV",
            data=pos_csv,
            file_name="edap_position_stats.csv",
            mime="text/csv",
        )

    # Show summary
    with st.expander("View Summary"):
        st.text(exporter.to_summary())


def render_regex_inference(result):
    """Render inferred regex patterns."""
    st.subheader("🔍 Inferred Regex Patterns")

    builder = RegexBuilder(result)

    specificity = st.radio(
        "Pattern Specificity",
        ["generic", "specific", "exact"],
        horizontal=True,
        help="""
        - **generic**: Standard classes like [A-Z], [a-z], [0-9]
        - **specific**: Uses actual characters seen at each position
        - **exact**: Most restrictive, only observed character combinations
        """
    )

    patterns = builder.build_all_patterns(specificity=specificity)

    if patterns:
        for length in sorted(patterns.keys()):
            with st.expander(f"Length {length} ({len(patterns[length])} patterns)"):
                for i, pattern in enumerate(patterns[length][:10]):
                    st.code(pattern)

        # Export patterns
        all_patterns = []
        for length_patterns in patterns.values():
            all_patterns.extend(length_patterns)

        st.download_button(
            "📥 Download All Patterns",
            data='\n'.join(all_patterns),
            file_name="edap_patterns.txt",
        )
    else:
        st.info("No patterns to display")


def main():
    """Main application entry point."""
    init_session_state()
    render_header()

    st.divider()

    # Sidebar for input
    words, min_length, max_length = render_sidebar()

    # Main area
    if not words:
        st.info("👈 Upload a wordlist or paste words in the sidebar to get started.")

        # Show help
        with st.expander("ℹ️ How to use EDAP"):
            st.markdown("""
            **EDAP** analyzes wordlists to learn patterns and generate new strings.

            **Steps:**
            1. **Input**: Upload a file, paste words, or use sample data
            2. **Analyze**: Click "Run Analysis" to analyze patterns
            3. **Generate**: Configure options and generate new strings
            4. **Export**: Download results in various formats

            **Generation Modes:**
            - **Smart**: Uses character co-occurrence (characters that appear together)
            - **Random**: Random selection from observed characters at each position
            - **Pattern**: Follows character type patterns (Upper/lower/digit/symbol)
            - **Regex**: Generate strings matching a custom regex pattern
            - **Markov**: Uses n-gram transitions learned from input (generates similar strings)
            - **Hybrid**: Combines multiple generators with weighted probability

            **Post-processing:**
            - **Mutations**: Apply hashcat-style transformations (leetspeak, case changes, appends)
            - **Filters**: Filter by length, character types, strength score, or regex patterns

            **Analysis Export:**
            - Export statistics as JSON, CSV, or position-level CSV
            - View detailed summary of character distributions

            **Use Cases:**
            - Security research & password analysis
            - Generating targeted wordlists
            - Creating test data matching specific formats
            - Password strength analysis
            """)
        return

    # Show current input preview
    with st.expander(f"📋 Current Input ({len(words)} words)", expanded=False):
        st.text_area(
            "Input words",
            value='\n'.join(words[:100]) + ('\n...' if len(words) > 100 else ''),
            height=150,
            disabled=True,
            label_visibility="collapsed",
        )

    # Analysis section
    col1, col2 = st.columns([1, 4])
    with col1:
        analyze_btn = st.button("🔬 Run Analysis", type="primary", use_container_width=True)

    # Check if analysis matches current input
    input_matches = (st.session_state.input_words == words) if st.session_state.analysis_result else False

    if st.session_state.analysis_result and not input_matches:
        st.warning("⚠️ Input has changed! Click 'Run Analysis' to analyze the new input.")

    if analyze_btn:
        with st.spinner("Analyzing patterns..."):
            result = run_analysis(words, min_length, max_length)
        st.success(f"Analyzed {result.total_words} words!")

    # Show results if analysis exists
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result

        render_analysis_results(result)

        st.divider()

        # Generation section
        gen_options = render_generation_options()

        # Mutation and filter options in expander
        with st.expander("🔧 Post-processing Options", expanded=False):
            mutation_options = render_mutation_options()
            st.divider()
            filter_options = render_filter_options()

        export_options = render_export_options()

        col1, col2 = st.columns([1, 4])
        with col1:
            generate_btn = st.button("🎲 Generate", type="primary", use_container_width=True)

        if generate_btn:
            with st.spinner(f"Generating {gen_options['count']} strings..."):
                try:
                    generated = run_generation(result, gen_options)
                    st.session_state.generated_words = generated
                    st.session_state.mutation_options = mutation_options
                    st.session_state.filter_options = filter_options
                    st.success(f"Generated {len(generated)} strings!")
                except Exception as e:
                    st.error(f"Generation error: {str(e)}")
                    st.session_state.generated_words = []

        # Show generated words
        if st.session_state.generated_words:
            # Use stored options for consistency
            m_opts = st.session_state.get('mutation_options', mutation_options)
            f_opts = st.session_state.get('filter_options', filter_options)
            render_generated_results(
                st.session_state.generated_words,
                gen_options,
                export_options,
                m_opts,
                f_opts,
            )

        st.divider()

        # Stats export section
        with st.expander("📈 Export Analysis Statistics"):
            render_stats_export(result)

        # Regex inference section
        with st.expander("🔍 Infer Regex Patterns from Data"):
            render_regex_inference(result)


if __name__ == "__main__":
    main()
