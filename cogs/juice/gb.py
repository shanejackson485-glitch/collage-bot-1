import discord
from discord.ext import commands
from discord import app_commands, ui
import os
import re
import string
import unicodedata
import copy
from bs4 import BeautifulSoup


from .helpers import era_colors, era_images, era_mapping


GB_HTML_FILE = os.path.join(os.getcwd(), "JuiceInfoDB", "gb.html")





class ProjectSelect(ui.Select):
    def __init__(self, results: list, embed_builder):
        self.results = results
        self.embed_builder = embed_builder

        options = [
            discord.SelectOption(
                label=entry.get("Project", "Unknown").splitlines()[0][:100], 
                value=str(i)
            ) for i, entry in enumerate(results)
        ]
        super().__init__(placeholder="Multiple results found. Choose one...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_index = int(self.values[0])
        selected_entry = self.results[selected_index]
        embed = self.embed_builder(selected_entry)
        await interaction.response.edit_message(embed=embed, view=self.view)

class ProjectSelectView(ui.View):
    def __init__(self, results: list, embed_builder):
        super().__init__(timeout=180)
        self.add_item(ProjectSelect(results, embed_builder))





class JuiceGBCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.era_mapping = era_mapping
        self.era_images = era_images
        self.era_colors = era_colors


    def load_gb_html(self):
        if not os.path.exists(GB_HTML_FILE): 
            return None
        with open(GB_HTML_FILE, "r", encoding="utf-8") as f: 
            return BeautifulSoup(f, "html.parser")

    def normalize_text(self, text: str) -> str:
        """Normalizes text for searching (lowercase, accents, punctuation)."""
        text = text.lower()

        text = ''.join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )

        text = re.sub(rf"[{re.escape(string.punctuation)}]", "", text)
        return text.strip()

    def clean_text(self, text):
        return text.strip().replace("\xa0", " ") if text else ""

    def parse_checkbox(self, cell):
        if not cell: return "N/A"
        svg = cell.find("svg")
        if not svg: return "N/A"
        use_tag = svg.find("use")
        if not use_tag: return "N/A"
        href = (use_tag.get("href") or use_tag.get("xlink:href") or "").lower().strip()
        if "unchecked-checkbox-id" in href: return "❌ No"
        elif "checked-checkbox-id" in href: return "✅ Yes"
        else: return "N/A"

    def _normalize_rowspans(self, soup):
        for table in soup.find_all("table"):
            grid = []
            for r_idx, row in enumerate(table.find_all("tr")):
                while len(grid) <= r_idx: grid.append([])
                c_idx = 0
                for cell in row.find_all(['th', 'td'], recursive=False):
                    while c_idx < len(grid[r_idx]) and grid[r_idx][c_idx] is not None: c_idx += 1
                    rowspan, colspan = int(cell.get('rowspan', 1)), int(cell.get('colspan', 1))
                    for i in range(rowspan):
                        for j in range(colspan):
                            r, c = r_idx + i, c_idx + j
                            while len(grid) <= r: grid.append([])
                            while len(grid[r]) <= c: grid[r].append(None)
                            if i == 0 and j == 0: grid[r][c] = cell
                            else:
                                placeholder_cell = copy.copy(cell)
                                if 'rowspan' in placeholder_cell.attrs: del placeholder_cell['rowspan']
                                if 'colspan' in placeholder_cell.attrs: del placeholder_cell['colspan']
                                grid[r][c] = placeholder_cell
                    c_idx += colspan
            all_rows = table.find_all("tr")
            for r_idx, row_cells in enumerate(grid):
                if r_idx < len(all_rows):
                    tr = all_rows[r_idx]
                    for cell in tr.find_all(['th', 'td']): cell.extract()
                    for cell in row_cells:
                        if cell: tr.append(cell)
        return soup

    def search_gb_entries(self, query: str):
        soup = self.load_gb_html()
        if not soup: return []
        soup = self._normalize_rowspans(soup)
        query_norm = self.normalize_text(query)
        results = []
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if not cols: continue
            
            def get_col_text(idx):
                if idx >= len(cols): return ""
                c = cols[idx]
                for br in c.find_all("br"):
                    br.replace_with("||BR||") 
                text = c.get_text(strip=True)
                return text.replace("||BR||", "\n")
            
            def get_col_cell(idx): return cols[idx] if idx < len(cols) else None
            
            project_text = self.clean_text(get_col_text(3))
            if not project_text or query_norm not in self.normalize_text(project_text):
                continue

            results.append({
                "Era": self.clean_text(get_col_text(1)), "Project": project_text,
                "Additional Info": self.clean_text(get_col_text(4)), "Price": self.clean_text(get_col_text(5)),
                "Start Date": self.clean_text(get_col_text(6)), "End Date": self.clean_text(get_col_text(7)),
                "Finished": self.parse_checkbox(get_col_cell(8)), "Surfaced": self.parse_checkbox(get_col_cell(9)),
            })
        return results

    def build_gb_embed(self, entry):
        short_era = entry.get("Era", "N/A")
        full_era = self.era_mapping.get(short_era, short_era)
        color = self.era_colors.get(full_era, 0x2F3136)
        thumbnail_url = self.era_images.get(full_era, "https://i.ibb.co/QF7dCqWY/posthumous.webp")
        
        raw_title = entry.get("Project", "Unknown Project")
        cleaned_title = raw_title.replace('*', '\n')
        title_lines = [line.strip() for line in cleaned_title.split('\n') if line.strip()]
        project_title = '\n'.join(title_lines)

        embed = discord.Embed(title=project_title, description="Group Buy / Project Info", color=color)

        def add_field(name, value):
            if value and value not in ["-", ""]:
                embed.add_field(name=name, value=value, inline=False)

        add_field("Era", full_era)
        add_field("Additional Info", entry.get("Additional Info"))
        price = entry.get("Price") if entry.get("Price") and entry.get("Price") != "FIND" else "N/A"
        add_field("Price", price)
        
        start_raw = entry.get("Start Date")
        start = start_raw.replace("Start Date", "").strip() if start_raw and start_raw != "FIND" else "N/A"
        end_raw = entry.get("End Date")
        end = end_raw.replace("End Date", "").strip() if end_raw and end_raw != "FIND" else "N/A"
        
        add_field("Dates", f"**Start:** {start}\n**End:** {end}")
        add_field("Finished", entry.get("Finished"))
        add_field("Surfaced with OG File", entry.get("Surfaced"))
        embed.set_thumbnail(url=thumbnail_url)
        return embed

    @commands.hybrid_command(name="juicegb", description="Search the Juice WRLD Group Buy Database.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def juicegb(self, ctx, *, query: str):
        await ctx.defer()
        
        if not os.path.exists(GB_HTML_FILE):
             await ctx.reply(f"❌ Database file not found at `{GB_HTML_FILE}`", mention_author=False)
             return

        results = self.search_gb_entries(query)
        if not results:
            await ctx.reply(f"❌ No results found for `{query}`.", mention_author=False)
        elif len(results) == 1:
            embed = self.build_gb_embed(results[0])
            await ctx.reply(embed=embed, mention_author=False)
        else:
            view = ProjectSelectView(results=results, embed_builder=self.build_gb_embed)
            initial_embed = self.build_gb_embed(results[0])
            await ctx.reply(embed=initial_embed, view=view, mention_author=False)

async def setup(bot):
    await bot.add_cog(JuiceGBCog(bot))