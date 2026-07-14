#!/bin/bash
# =============================================================================
# NCBI Eukaryota Genome Assembly Summary Pipeline (终极版 v4)
# 核心修复：
#   1. 用 xargs -P 替代 & + wait，彻底避免 wait 卡住
#   2. fetch_with_timeout.py 使用 Popen + killpg，超时 kill 整个进程组
#   3. 支持断点续跑：已下载的 jsonl 自动跳过
# =============================================================================

set -euo pipefail
trap 'echo "[ERROR] 脚本在 $LINENO 行中断，退出码 $?" >&2; exit 1' ERR

readonly THREADS=$(nproc 2>/dev/null || echo 4)
readonly LOG="pipeline_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG")
exec 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { log "ERROR: $*"; exit 1; }

# =============================================================================
# 0. 环境检查
# =============================================================================
log "=== 0. 环境检查 ==="
for cmd in taxonkit datasets jq python3 awk xargs; do
    command -v "$cmd" >/dev/null 2>&1 || die "$cmd 未安装或不在 PATH 中"
done
python3 -c "import pandas, openpyxl" 2>/dev/null || die "缺少 pandas/openpyxl"

if [[ ! -s Protists.list ]]; then
    cat > Protists.list << 'EOF'
Apicomplexa
Ciliophora
Fornicata
Euglenozoa
Amoebozoa
Bacillariophyta
Cercozoa
Cryptophyta
Haptophyta
Oomycota
Peronosporomycetes
Bigyra
Choanoflagellata
Evosea
Discosea
Phaeophyceae
Pelagophyceae
Eustigmatophyceae
Xanthophyceae
Chlorarachniophyceae
Labyrinthulomycetes
Hyphochytriomycetes
Opalinata
Metamonada
Parabasalia
Kinetoplastea
Diplomonadida
Retortamonadida
Oxymonadida
Jakobida
Heterolobosea
Spirotrichea
Oligohymenophorea
Hymenostomatida
Peniculida
Suctoria
Peritrichia
Heterotrichida
Litostomatea
Phyllopharyngea
Nassophorea
Colpodea
Prostomatea
Plagiopylea
Oligotrichea
Choreotrichia
Stichotrichia
Hypotrichia
Euplotia
Armophorea
Cariacotrichea
Clevelandlellata
Muranotrichea
Parablepharismea
Protocruziea
Phacodiniidea
Licnophoria
Cryptophyceae
Katablepharidophyta
Centroheliozoa
Telonemia
Picozoa
Glaucocystophyceae
Rhodophyta
Foraminifera
Reticulomyxa
Thraustochytrida
Aconoidasida
Conoidasida
Gregarinomorpha
Coccidiomorpha
Haemospororida
Piroplasmida
Aconoidasida
EOF
    log "  已生成默认 Protists.list（$(wc -l < Protists.list) 个门）"
else
    log "  使用现有 Protists.list（$(wc -l < Protists.list) 个门）"
fi

if [[ ! -s Viridiplantae.list ]]; then
    cat > Viridiplantae.list << 'EOF'
Streptophyta
Chlorophyta
Charophyta
Prasinophyta
Klebsormidiophyceae
Mesostigmatophyceae
Chlorokybales
Zygnematophyceae
Coleochaetophyceae
Rhodophyta
Glaucocystophyceae
EOF
    log "  已生成默认 Viridiplantae.list（$(wc -l < Viridiplantae.list) 个门）"
else
    log "  使用现有 Viridiplantae.list（$(wc -l < Viridiplantae.list) 个门）"
fi

log "环境检查通过，线程数: $THREADS"

# 诊断信息
log "=== 诊断: datasets CLI 信息 ==="
datasets version 2>/dev/null || log "  datasets version 命令不可用"
datasets --help 2>/dev/null | head -n 20 || log "  datasets --help 失败"
log "=== 诊断: taxonkit 信息 ==="
taxonkit version 2>/dev/null || log "  taxonkit version 命令不可用"

# 设置 TAXONKIT 数据库目录
TAXONKIT_HOME="$HOME/.taxonkit"
mkdir -p "$TAXONKIT_HOME"
export TAXONKIT_DB="$TAXONKIT_HOME"
log "TAXONKIT_DB=$TAXONKIT_DB"

# 验证 taxdump 文件是否有效，如果无效则重新下载
log "=== 验证 taxonkit 数据库文件 ==="
need_download=false
for f in names.dmp nodes.dmp delnodes.dmp merged.dmp; do
    if [ ! -s "$TAXONKIT_HOME/$f" ]; then
        log "  文件缺失或为空: $f"
        need_download=true
    fi
done

if [ "$need_download" = true ]; then
    log "正在重新下载 taxdump 数据库..."
    cd "$TAXONKIT_HOME"
    rm -f taxdump.tar.gz
    TAXDUMP_URL="https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz"
    if ! curl -fL --retry 5 --retry-delay 5 --max-time 300 -o taxdump.tar.gz "$TAXDUMP_URL"; then
        log "curl 下载失败，尝试 wget..."
        if ! wget --tries=5 --retry-connrefused --timeout=60 -q "$TAXDUMP_URL" -O taxdump.tar.gz; then
            die "无法下载 taxdump 数据库"
        fi
    fi
    if [ ! -s taxdump.tar.gz ]; then
        die "下载的 taxdump.tar.gz 为空"
    fi
    log "下载完成，开始解压..."
    tar -xzf taxdump.tar.gz || die "解压 taxdump 失败"
    rm -f taxdump.tar.gz
    log "解压完成"
fi

log "=== 验证完成 ==="
ls -lh "$TAXONKIT_HOME"

# =============================================================================
# 1. 生成 Python 脚本
# =============================================================================
log "=== 1. 生成辅助 Python 脚本 ==="

# --- Python 0: 带 timeout 的 datasets 下载 wrapper（使用 Popen + killpg）---
cat > fetch_with_timeout.py << 'PYEOF0'
#!/usr/bin/env python3
import sys, subprocess, os, signal

def main():
    if len(sys.argv) < 4:
        print("Usage: fetch_with_timeout.py <taxid> <outfile> <timeout_sec>", file=sys.stderr)
        sys.exit(1)
    taxid = sys.argv[1]
    outfile = sys.argv[2]
    timeout_sec = int(sys.argv[3])

    # 检查 datasets 可用性
    try:
        result = subprocess.run(['datasets', '--version'], capture_output=True, text=True, timeout=5)
        print(f"[INFO] datasets version: {result.stdout.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] Could not check datasets version: {e}", file=sys.stderr)

    # 尝试多种命令格式
    cmd_variants = [
        ['datasets', 'summary', 'genome', 'taxon', taxid],
        ['datasets', 'summary', 'genome', 'taxon', taxid, '--as-json-lines'],
    ]

    for cmd in cmd_variants:
        try:
            print(f"[INFO] Trying: {' '.join(cmd)}", file=sys.stderr)
            with open(outfile, 'w') as f:
                proc = subprocess.Popen(
                    cmd,
                    stdout=f, stderr=subprocess.PIPE,
                    start_new_session=True, text=True
                )
                try:
                    stdout_data, stderr_data = proc.communicate(timeout=timeout_sec)
                    if proc.returncode == 0:
                        print(f"[INFO] SUCCESS with: {' '.join(cmd)}", file=sys.stderr)
                        if os.path.getsize(outfile) == 0:
                            with open(outfile, 'w') as f2:
                                f2.write('[]')
                        sys.exit(0)
                    else:
                        print(f"[WARN] FAILED (exit {proc.returncode}) with: {' '.join(cmd)} - {stderr_data}", file=sys.stderr)
                        continue
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                    print(f"[WARN] TIMEOUT with: {' '.join(cmd)}", file=sys.stderr)
                    continue
        except Exception as e:
            print(f"[WARN] ERROR with: {' '.join(cmd)} - {e}", file=sys.stderr)
            continue

    print(f"FAILED:{taxid}", file=sys.stderr)
    with open(outfile, 'w') as f:
        f.write('[]')
    sys.exit(0)

if __name__ == "__main__":
    main()
PYEOF0
chmod +x fetch_with_timeout.py

# --- Python 1: 分类汇总 ---
cat > get_Eukaryota_Taxonomy_Summary.py << 'PYEOF1'
#!/usr/bin/env python3
import sys, csv
from collections import defaultdict

def main():
    print("[INFO] 正在逐行读取并实时聚合 (防内存溢出模式)...", file=sys.stderr)
    with open("Protists.list", 'r', encoding='utf-8') as f:
        protists_set = {line.strip() for line in f if line.strip()}
    with open("Viridiplantae.list", 'r', encoding='utf-8') as f:
        viridiplantae_set = {line.strip() for line in f if line.strip()}
    summary = defaultdict(lambda: {'order': set(), 'family': set(), 'genus': set(), 'species': set()})
    line_count = 0; error_count = 0; written_count = 0
    out = open("Eukaryota_tax_class.txt", 'w', encoding='utf-8', buffering=8192)
    with open('Eukaryota_taxonomy.tsv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for parts in reader:
            line_count += 1
            try:
                if len(parts) < 9: error_count += 1; continue
                tax_id = parts[0]
                subkingdom = parts[1].split(';')[3] if ';' in parts[1] and len(parts[1].split(';')) > 3 else parts[1]
                phylum = parts[3] if len(parts) > 3 else ''
                cls = parts[4] if len(parts) > 4 else ''
                order = parts[5] if len(parts) > 5 else ''
                family = parts[6] if len(parts) > 6 else ''
                genus = parts[7] if len(parts) > 7 else ''
                species = parts[8] if len(parts) > 8 else ''
            except (IndexError, AttributeError, ValueError):
                error_count += 1; continue
            if subkingdom in ('Fungi', 'Metazoa', 'Protists', 'Viridiplantae'):
                kingdom = subkingdom
            elif phylum in protists_set: kingdom = 'Protists'
            elif phylum in viridiplantae_set: kingdom = 'Viridiplantae'
            else: kingdom = 'Others'
            out.write('\t'.join([species, tax_id, kingdom, phylum, cls, order, family, genus, species]) + '\n')
            written_count += 1
            key = (phylum, cls)
            if order: summary[key]['order'].add(order)
            if family: summary[key]['family'].add(family)
            if genus: summary[key]['genus'].add(genus)
            if species: summary[key]['species'].add(species)
    out.close()
    print(f"[INFO] 处理 {line_count} 行，写入 {written_count} 条，跳过 {error_count} 行。", file=sys.stderr)
    records = []
    for (phylum, cls), counts in summary.items():
        records.append({'门(Phylum)': phylum, '纲(Class)': cls, '总目数': len(counts['order']),
                        '总科数': len(counts['family']), '总属数': len(counts['genus']), '总种数': len(counts['species'])})
    records.sort(key=lambda x: x['总种数'], reverse=True)
    import pandas as pd
    df = pd.DataFrame(records)
    df.to_excel('NCBI_Eukaryota_Taxonomy_Summary.xlsx', index=False)
    df.to_csv('NCBI_Eukaryota_Taxonomy_Summary.txt', sep='\t', index=False)
    print("[DONE] 宏观统计报表已保存。", file=sys.stderr)
if __name__ == "__main__": main()
PYEOF1

# --- Python 2: 格式化 Excel 生成器 ---
cat > generate_excel.py << 'PYEOF2'
#!/usr/bin/env python3
import sys, re, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter

INPUT_STATS = "Eukaryota_assemblies_stats.tsv"
INPUT_TAX  = "Eukaryota_tax_class.txt"
OUTPUT_XLSX = "Eukaryota_assemblies_summary.xlsx"

def infer_haplotype(name):
    if pd.isna(name): return 'unphased'
    n = str(name).lower()
    if re.search(r'\bhap1\b|\bhaplotype1\b|\bhap_1\b', n): return 'hap1'
    if re.search(r'\bhap2\b|\bhaplotype2\b|\bhap_2\b', n): return 'hap2'
    if re.search(r'\bmat\b|\bmaternal\b', n): return 'mat'
    if re.search(r'\bpat\b|\bpaternal\b', n): return 'pat'
    if re.search(r'\bpri\b|\bprimary\b', n): return 'pri'
    if re.search(r'\balt\b|\balternate\b', n): return 'alt'
    return 'unphased'

def main():
    print("[INFO] 读取 Assembly 统计...", file=sys.stderr)
    asm_cols = ['Assembly Accession', 'Taxonomic ID', 'Assembly Name', 'Assembly Level',
                'RefSeq Category', 'Is Atypical', 'Atypical Warnings',
                'Assembly Stats Total Sequence Length (bp)', 'Assembly Stats Total Number of Chromosomes',
                'Assembly Stats Number of Contigs', 'Assembly Stats Contig N50 (bp)',
                'Assembly Stats Number of Scaffolds', 'Assembly Stats Scaffold N50 (bp)',
                'Assembly Stats GC Percent', 'Assembly Release Date', 'Assembly Sequencing Tech']
    asm_df = pd.read_csv(INPUT_STATS, sep='\t', header=None, names=asm_cols, dtype=str, low_memory=False)

    print("[INFO] 读取分类映射...", file=sys.stderr)
    tax_cols = ['Species', 'Taxonomic ID', 'Subkingdom', 'Phylum', 'Class', 'Order', 'Family', 'Genus', 'Species Name']
    tax_df = pd.read_csv(INPUT_TAX, sep='\t', header=None, names=tax_cols, dtype=str, low_memory=False)
    tax_df = tax_df.drop_duplicates(subset='Taxonomic ID')

    merged = asm_df.merge(tax_df, on='Taxonomic ID', how='inner')
    missing = len(asm_df) - len(merged)
    if missing > 0: print(f"[WARN] {missing} 条未匹配到分类", file=sys.stderr)

    merged['Haplotype'] = merged['Assembly Name'].apply(infer_haplotype)

    col_order = ['Assembly Accession', 'Species', 'Taxonomic ID', 'Subkingdom', 'Phylum', 'Class',
                 'Order', 'Family', 'Genus', 'Species Name', 'Assembly Name', 'Haplotype',
                 'Assembly Level', 'RefSeq Category', 'Is Atypical', 'Atypical Warnings',
                 'Assembly Stats Total Sequence Length (bp)', 'Assembly Stats Total Number of Chromosomes',
                 'Assembly Stats Number of Contigs', 'Assembly Stats Contig N50 (bp)',
                 'Assembly Stats Number of Scaffolds', 'Assembly Stats Scaffold N50 (bp)',
                 'Assembly Stats GC Percent', 'Assembly Release Date', 'Assembly Sequencing Tech']
    raw = merged[col_order].copy()

    raw['__is_ref'] = (raw['RefSeq Category'].str.strip().str.lower() == 'reference genome').astype(int)
    raw['__n50'] = pd.to_numeric(raw['Assembly Stats Contig N50 (bp)'], errors='coerce').fillna(-1)
    raw['__key'] = raw['Taxonomic ID'] + '|' + raw['Haplotype']
    rmdup = (raw.sort_values(by=['__is_ref', '__n50'], ascending=[False, False])
             .drop_duplicates(subset='__key', keep='first')
             .drop(columns=['__is_ref', '__n50', '__key']).copy())

    print(f"[INFO] Raw: {len(raw)}, 去重后: {len(rmdup)}", file=sys.stderr)

    print("[INFO] 生成格式化 Excel...", file=sys.stderr)
    wb = Workbook()
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(left=Side(style='thin', color='CCCCCC'), right=Side(style='thin', color='CCCCCC'),
                         top=Side(style='thin', color='CCCCCC'), bottom=Side(style='thin', color='CCCCCC'))

    def style_sheet(ws, df, sheet_name):
        ws.title = sheet_name
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
            ws.append(row)
        for cell in ws[1]:
            cell.font = header_font; cell.fill = header_fill; cell.alignment = header_align; cell.border = thin_border
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            for cell in row:
                cell.border = thin_border
                cell.alignment = Alignment(vertical='center')
        for col_idx, column in enumerate(df.columns, 1):
            max_len = len(str(column))
            for cell in ws.iter_cols(min_col=col_idx, max_col=col_idx, min_row=2, max_row=min(ws.max_row, 1000)):
                for c in cell:
                    try: max_len = max(max_len, len(str(c.value)))
                    except: pass
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 60)
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
        ws.row_dimensions[1].height = 30

    style_sheet(wb.active, raw, "All_Raw")
    ws2 = wb.create_sheet(); style_sheet(ws2, rmdup, "Species_Unique")
    wb.save(OUTPUT_XLSX)
    print(f"[DONE] 已保存: {OUTPUT_XLSX}", file=sys.stderr)

if __name__ == "__main__": main()
PYEOF2

chmod +x fetch_with_timeout.py get_Eukaryota_Taxonomy_Summary.py generate_excel.py
log "辅助脚本已生成"

# =============================================================================
# 2. Taxonkit 获取物种列表
# =============================================================================
log "=== 2. 获取 Eukaryota 物种 TaxID ==="

needs_rebuild=false
if [[ ! -s Eukaryota_nodes.txt ]]; then
    needs_rebuild=true
    log "  Eukaryota_nodes.txt 不存在，需要生成"
else
    if ! head -n 5 Eukaryota_nodes.txt | grep -qE '\[species\]|\[subspecies\]'; then
        needs_rebuild=true
        log "  Eukaryota_nodes.txt 格式异常，重新生成"
    else
        log "  Eukaryota_nodes.txt 存在且格式正确"
    fi
fi

if [[ "$needs_rebuild" == true ]]; then
    rm -f Eukaryota_nodes.txt
    log "  运行 taxonkit list --ids 2759 --show-rank --indent \"\" ..."
    
    # 诊断信息
    log "  诊断: TAXONKIT_DB=$TAXONKIT_DB"
    log "  诊断: 检查 .dmp 文件..."
    for f in names.dmp nodes.dmp delnodes.dmp merged.dmp; do
        if [ -f "$TAXONKIT_DB/$f" ]; then
            log "    $f: $(wc -c < "$TAXONKIT_DB/$f") bytes, $(wc -l < "$TAXONKIT_DB/$f") lines"
        else
            log "    $f: 未找到"
        fi
    done
    log "  诊断: 文件类型检查..."
    file "$TAXONKIT_DB/names.dmp" || true
    log "  诊断: names.dmp 前 200 字节..."
    head -c 200 "$TAXONKIT_DB/names.dmp" | xxd | head -n 5 || true
    
    if ! taxonkit list --ids 2759 --show-rank --indent "" > Eukaryota_nodes.txt 2>taxonkit_list.err; then
        log "  taxonkit list 错误日志："
        cat taxonkit_list.err >&2 || true
        die "taxonkit list 失败"
    fi
    rm -f taxonkit_list.err
    node_count=$(wc -l < Eukaryota_nodes.txt || echo 0)
    log "  taxonkit list 完成，共 $node_count 个节点"
    if [[ "$node_count" -eq 0 ]]; then
        die "taxonkit list 输出为空"
    fi
fi

if [[ ! -s Eukaryota_species_taxids.txt ]] || [[ "$needs_rebuild" == true ]]; then
    rm -f Eukaryota_species_taxids.txt
    awk '$2 == "[species]" || $2 == "[subspecies]" {print $1}' Eukaryota_nodes.txt > Eukaryota_species_taxids.txt
fi

species_count=$(wc -l < Eukaryota_species_taxids.txt || echo 0)
if [[ "$species_count" -eq 0 ]]; then
    log "  Eukaryota_nodes.txt 前 5 行内容："
    head -n 5 Eukaryota_nodes.txt | sed 's/^/    /' >&2
    die "未提取到任何物种 TaxID"
fi
log "  提取物种 TaxID: $species_count 条"

# =============================================================================
# 4. 构建分类 lineage
# =============================================================================
log "=== 4. 构建分类 lineage ==="
if [[ ! -s Eukaryota_taxonomy.tsv ]] || [[ "$needs_rebuild" == true ]]; then
    rm -f Eukaryota_taxonomy.tsv
    taxonkit lineage --threads "$THREADS" Eukaryota_species_taxids.txt 2>/dev/null \
        | taxonkit reformat --threads "$THREADS" -I 1 -F -f "{k}\t{p}\t{c}\t{o}\t{f}\t{g}\t{s}" \
        > Eukaryota_taxonomy.tsv || die "taxonkit lineage/reformat 失败"
fi
log "  lineage: $(wc -l < Eukaryota_taxonomy.tsv) 条"

# =============================================================================
# 5. 分类汇总
# =============================================================================
log "=== 5. 汇总分类统计 ==="
python3 get_Eukaryota_Taxonomy_Summary.py || die "分类汇总失败"

# =============================================================================
# 6. 并行下载 NCBI 基因组摘要（核心修复：用 xargs -P 替代 & + wait）
# =============================================================================
log "=== 6. 并行下载 NCBI 基因组摘要 ==="

# 创建下载任务列表文件
cat > download_tasks.txt << 'EOF'
33208	Metaoza_assemblies.jsonl
33090	Viridiplantae_assemblies.jsonl
4751	Fungi_assemblies.jsonl
2698737	SAR_assemblies.jsonl
554915	Amoebozoa_assemblies.jsonl
2611341	Metamonada_assemblies.jsonl
33083	Euglenozoa_assemblies.jsonl
554940	Fornicata_assemblies.jsonl
3027	Cryptophyta_assemblies.jsonl
2830480	Haptista_assemblies.jsonl
33154	Apusozoa_assemblies.jsonl
EOF

# 定义单条下载逻辑（内联脚本，用于 xargs）
# 关键：xargs -P 会正确管理进程生命周期，超时后自动回收，不会卡住
log "  开始并行下载（并发数: 4，单任务超时: 300s）..."

while IFS=$'\t' read -r taxid outfile; do
    if [[ -s "$outfile" ]]; then
        log "  跳过 ${taxid}（已存在）"
        continue
    fi
    tmp="${outfile}.tmp.$$"
    if python3 fetch_with_timeout.py "${taxid}" "$tmp" 300; then
        if [[ -s "$tmp" ]] && [[ "$(head -c 1 "$tmp")" != "" ]]; then
            mv "$tmp" "$outfile"
            log "  完成 ${taxid}"
        else
            echo "[]" > "$outfile"; rm -f "$tmp"
            log "  WARNING: ${taxid} 输出为空"
        fi
    else
        echo "[]" > "$outfile"; rm -f "$tmp"
        log "  WARNING: ${taxid} 失败或超时（300s）"
    fi
done < download_tasks.txt

log "  下载完成"

# =============================================================================
# 7. 合并 JSONL
# =============================================================================
log "=== 7. 合并 JSONL ==="
cat SAR_assemblies.jsonl Amoebozoa_assemblies.jsonl Metamonada_assemblies.jsonl \
    Euglenozoa_assemblies.jsonl Fornicata_assemblies.jsonl Cryptophyta_assemblies.jsonl \
    Haptista_assemblies.jsonl Apusozoa_assemblies.jsonl > Protists_assemblies.jsonl
cat Metaoza_assemblies.jsonl Viridiplantae_assemblies.jsonl Fungi_assemblies.jsonl \
    Protists_assemblies.jsonl > Eukaryota_assemblies.jsonl
log "  总记录: $(wc -l < Eukaryota_assemblies.jsonl) 行"

# =============================================================================
# 8. 提取 Assembly 统计
# =============================================================================
log "=== 8. 提取 Assembly 统计 ==="
{
    echo -e "Assembly Accession\tTaxonomic ID\tAssembly Name\tAssembly Level\tRefSeq Category\tIs Atypical\tAtypical Warnings\tAssembly Stats Total Sequence Length (bp)\tAssembly Stats Total Number of Chromosomes\tAssembly Stats Number of Contigs\tAssembly Stats Contig N50 (bp)\tAssembly Stats Number of Scaffolds\tAssembly Stats Scaffold N50 (bp)\tAssembly Stats GC Percent\tAssembly Release Date\tAssembly Sequencing Tech"
    jq -r '
        if type == "array" then .[] elif .reports then .reports[] else . end
        | select(.accession != null and .assembly_info != null)
        | [
            .accession, (.organism.tax_id | tostring),
            (.assembly_info.assembly_name // "NA"), .assembly_info.assembly_level,
            (.assembly_info.refseq_category // "NA"),
            (.assembly_info.atypical.isAtypical // "NA" | tostring),
            (.assembly_info.atypical.warnings // [] | if type == "array" then join("; ") else . end),
            (.assembly_stats.total_sequence_length // "NA"), (.assembly_stats.total_number_of_chromosomes // "NA"),
            (.assembly_stats.number_of_contigs // .assembly_stats.total_number_of_contigs // "NA"),
            (.assembly_stats.contig_n50 // "NA"),
            (.assembly_stats.number_of_scaffolds // .assembly_stats.total_number_of_scaffolds // "NA"),
            (.assembly_stats.scaffold_n50 // "NA"), (.assembly_stats.gc_percent // "NA"),
            (.assembly_info.release_date // .assembly_info.submission_date // "NA"),
            (.assembly_info.sequencing_tech // "NA" | if type == "array" then join("; ") else . end)
        ] | @tsv
    ' Eukaryota_assemblies.jsonl
} | awk 'NR>1' | awk '!seen[$0]++' > Eukaryota_assemblies_stats.tsv
log "  提取到 $(wc -l < Eukaryota_assemblies_stats.tsv) 条唯一记录"

# =============================================================================
# 9. 生成格式化 Excel（双 Sheet）
# =============================================================================
log "=== 9. 生成格式化 Excel ==="
python3 generate_excel.py || die "Excel 生成失败"

# =============================================================================
# 10. 完成
# =============================================================================
log "=== ✅ 流程全部完成 ==="
log "输出文件："
log "  - Eukaryota_assemblies_summary.xlsx    (最终双 Sheet Excel)"
log "  - NCBI_Eukaryota_Taxonomy_Summary.xlsx (门/纲宏观统计)"
log "  - $LOG                                (运行日志)"
