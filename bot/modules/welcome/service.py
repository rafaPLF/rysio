from __future__ import annotations

from io import BytesIO
from pathlib import Path

import discord
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WELCOME_STYLE_NEON = "neon_card"
WELCOME_STYLE_RYSIO = "rysio_card"
RYSIO_ART_PATH = Path(__file__).resolve().parents[3] / "assets" / "welcome" / "rysioohnebg.png"


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, *, max_width: int, start_size: int, bold: bool = False):
    size = start_size
    while size >= 28:
        font = _load_font(size, bold=bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            return font
        size -= 2
    return _load_font(28, bold=bold)


async def build_welcome_card(member: discord.Member, *, guild_name: str, member_count: int) -> BytesIO:
    width, height = 1200, 540
    canvas = Image.new("RGBA", (width, height), (22, 28, 41, 255))
    draw = ImageDraw.Draw(canvas)

    # Background glow and accents
    accent = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    accent_draw = ImageDraw.Draw(accent)
    accent_draw.rounded_rectangle((105, 115, 500, 430), radius=52, fill=(36, 116, 216, 220))
    accent_draw.rounded_rectangle((730, 175, 1085, 485), radius=52, fill=(0, 212, 255, 220))
    accent = accent.filter(ImageFilter.GaussianBlur(8))
    canvas.alpha_composite(accent)

    # Main card
    card_bounds = (185, 95, 1015, 455)
    draw.rounded_rectangle(card_bounds, radius=58, fill=(29, 34, 39, 246))
    draw.rounded_rectangle((435, 112, 765, 160), radius=18, fill=(66, 71, 76, 255))

    badge_font = _load_font(26, bold=True)
    badge_text = f"Mitglied #{member_count}"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_width = badge_bbox[2] - badge_bbox[0]
    draw.text(((width - badge_width) / 2, 122), badge_text, font=badge_font, fill=(244, 244, 244, 255))

    avatar_bytes = await member.display_avatar.replace(size=256).read()
    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((168, 168))
    avatar_mask = Image.new("L", (168, 168), 0)
    ImageDraw.Draw(avatar_mask).ellipse((0, 0, 167, 167), fill=255)

    avatar_border = Image.new("RGBA", (188, 188), (0, 0, 0, 0))
    avatar_border_mask = Image.new("L", (188, 188), 0)
    ImageDraw.Draw(avatar_border_mask).ellipse((0, 0, 187, 187), fill=255)
    avatar_border_draw = ImageDraw.Draw(avatar_border)
    avatar_border_draw.ellipse((0, 0, 187, 187), fill=(255, 255, 255, 255))
    avatar_border.alpha_composite(avatar, (10, 10))

    avatar_x = (width - 188) // 2
    canvas.alpha_composite(avatar_border, (avatar_x, 174))

    welcome_text = f"Willkommen {member.display_name}"
    welcome_font = _fit_text(draw, welcome_text, max_width=680, start_size=58, bold=True)
    welcome_bbox = draw.textbbox((0, 0), welcome_text, font=welcome_font)
    welcome_width = welcome_bbox[2] - welcome_bbox[0]
    draw.text(((width - welcome_width) / 2, 370), welcome_text, font=welcome_font, fill=(248, 248, 248, 255))

    subtitle_top_font = _load_font(28, bold=True)
    subtitle_bottom_font = _fit_text(draw, guild_name, max_width=560, start_size=32, bold=True)
    subtitle_top = "bei"
    subtitle_top_bbox = draw.textbbox((0, 0), subtitle_top, font=subtitle_top_font)
    subtitle_top_width = subtitle_top_bbox[2] - subtitle_top_bbox[0]
    draw.text(((width - subtitle_top_width) / 2, 435), subtitle_top, font=subtitle_top_font, fill=(232, 232, 232, 255))

    subtitle_bottom_bbox = draw.textbbox((0, 0), guild_name, font=subtitle_bottom_font)
    subtitle_bottom_width = subtitle_bottom_bbox[2] - subtitle_bottom_bbox[0]
    draw.text(((width - subtitle_bottom_width) / 2, 468), guild_name, font=subtitle_bottom_font, fill=(255, 255, 255, 255))

    output = BytesIO()
    canvas.save(output, format="PNG")
    output.seek(0)
    return output


def _load_rysio_art(size: tuple[int, int]) -> Image.Image | None:
    if not RYSIO_ART_PATH.exists():
        return None
    try:
        image = Image.open(RYSIO_ART_PATH).convert("RGBA")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        return image
    except OSError:
        return None


async def build_rysio_welcome_card(member: discord.Member, *, guild_name: str, member_count: int) -> BytesIO:
    width, height = 1200, 540
    canvas = Image.new("RGBA", (width, height), (13, 19, 30, 255))
    draw = ImageDraw.Draw(canvas)

    # Blue atmospheric background.
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-80, -120, 560, 520), fill=(44, 121, 255, 150))
    glow_draw.ellipse((690, -80, 1290, 520), fill=(0, 205, 255, 110))
    glow_draw.ellipse((250, 260, 920, 760), fill=(17, 51, 115, 130))
    glow = glow.filter(ImageFilter.GaussianBlur(36))
    canvas.alpha_composite(glow)

    # Frame and panels.
    draw.rounded_rectangle((72, 68, 1128, 472), radius=48, fill=(19, 27, 40, 230), outline=(102, 164, 255, 60), width=2)
    draw.rounded_rectangle((112, 104, 540, 438), radius=38, fill=(14, 20, 31, 235))
    draw.rounded_rectangle((574, 104, 1088, 438), radius=38, fill=(23, 32, 47, 235))

    badge_font = _load_font(24, bold=True)
    badge_text = f"Mitglied #{member_count}"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_w = badge_bbox[2] - badge_bbox[0]
    draw.rounded_rectangle((470, 82, 730, 124), radius=16, fill=(47, 61, 85, 215))
    draw.text(((width - badge_w) / 2, 91), badge_text, font=badge_font, fill=(240, 246, 255, 255))

    art = _load_rysio_art((320, 320))
    if art is not None:
        art_x = 166 + (320 - art.width) // 2
        art_y = 112 + (320 - art.height) // 2
        art_glow = Image.new("RGBA", (370, 370), (0, 0, 0, 0))
        art_glow_draw = ImageDraw.Draw(art_glow)
        art_glow_draw.ellipse((22, 22, 348, 348), fill=(44, 132, 255, 120))
        art_glow = art_glow.filter(ImageFilter.GaussianBlur(18))
        canvas.alpha_composite(art_glow, (86, 92))
        canvas.alpha_composite(art, (art_x, art_y))
    else:
        placeholder_font = _load_font(42, bold=True)
        draw.rounded_rectangle((176, 144, 476, 404), radius=34, fill=(36, 49, 73, 255))
        draw.text((264, 243), "RYSIO", font=placeholder_font, fill=(231, 240, 255, 255))

    avatar_bytes = await member.display_avatar.replace(size=256).read()
    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((144, 144))
    avatar_mask = Image.new("L", (144, 144), 0)
    ImageDraw.Draw(avatar_mask).ellipse((0, 0, 143, 143), fill=255)
    avatar.putalpha(avatar_mask)

    avatar_ring = Image.new("RGBA", (164, 164), (0, 0, 0, 0))
    avatar_ring_draw = ImageDraw.Draw(avatar_ring)
    avatar_ring_draw.ellipse((0, 0, 163, 163), fill=(242, 248, 255, 255))
    avatar_ring.alpha_composite(avatar, (10, 10))
    canvas.alpha_composite(avatar_ring, (730, 132))

    headline = f"Willkommen {member.display_name}"
    headline_font = _fit_text(draw, headline, max_width=410, start_size=54, bold=True)
    headline_bbox = draw.textbbox((0, 0), headline, font=headline_font)
    headline_w = headline_bbox[2] - headline_bbox[0]
    draw.text((626 + (410 - headline_w) / 2, 312), headline, font=headline_font, fill=(247, 249, 255, 255))

    sub_font = _load_font(28, bold=True)
    sub_text = "ist jetzt auf dem Server"
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sub_w = sub_bbox[2] - sub_bbox[0]
    draw.text((626 + (410 - sub_w) / 2, 374), sub_text, font=sub_font, fill=(156, 196, 255, 255))

    guild_font = _fit_text(draw, guild_name, max_width=390, start_size=34, bold=True)
    guild_bbox = draw.textbbox((0, 0), guild_name, font=guild_font)
    guild_w = guild_bbox[2] - guild_bbox[0]
    draw.text((636 + (390 - guild_w) / 2, 410), guild_name, font=guild_font, fill=(255, 255, 255, 255))

    output = BytesIO()
    canvas.save(output, format="PNG")
    output.seek(0)
    return output


async def send_welcome_message(bot: discord.Client, member: discord.Member, *, channel: discord.TextChannel, style: str = "rysio_card") -> discord.Message:
    member_count = member.guild.member_count or 0
    if style == WELCOME_STYLE_RYSIO:
        image = await build_rysio_welcome_card(
            member,
            guild_name=member.guild.name,
            member_count=member_count,
        )
    else:
        image = await build_welcome_card(
            member,
            guild_name=member.guild.name,
            member_count=member_count,
        )
        style = WELCOME_STYLE_NEON

    file = discord.File(image, filename="welcome-card.png")
    embed = discord.Embed(color=discord.Color.blue())
    embed.set_image(url="attachment://welcome-card.png")
    embed.description = f"{member.mention} willkommen auf **{member.guild.name}**."
    return await channel.send(content=member.mention, embed=embed, file=file)
