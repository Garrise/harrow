import json
import random
import sys
import base64
from pathlib import Path
from graia.saya import Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Source
from graia.ariadne.message.parser.twilight import Twilight
from graia.ariadne.event.message import Group, GroupMessage
from graia.ariadne.message.parser.twilight import Twilight, RegexResult, UnionMatch, WildcardMatch
from graia.saya.builtins.broadcast.schema import ListenerSchema

from shared.utils.text2img import template2img
from shared.utils.module_related import get_command
from shared.utils.UI import ColumnList, ColumnListItem, ColumnListItemSwitch, GenForm, Column, one_mock_gen, ColumnTitle, ColumnImage, ColumnUserInfo
from shared.utils.control import (
    FrequencyLimit,
    Function,
    BlackListControl,
    UserCalledCountControl,
    Distribute
)

channel = Channel.current()
channel.name("Harrow")
channel.author("Garrise")
channel.description("可以使用哈罗牌占卜的插件，在群中发送 `哈罗牌` 后，在空格后面接 `占卜`或`抽卡`，例如 `哈罗牌 占卜`")

def get_img(card: {}):
    img_path = Path().cwd() / "modules" / "third_party" / "harrow" / "card" / f"{card['num']}.jpg"
    return f"data:image/jpg;base64,{base64.b64encode((img_path).read_bytes()).decode()}"

@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight([
                get_command(__file__, channel.module),
                UnionMatch("抽卡"),
                WildcardMatch() @ "question"
            ])
        ],
        decorators=[
            Distribute.distribute(),
            FrequencyLimit.require("harrow", 1),
            Function.require(channel.module, notice=True),
            BlackListControl.enable(),
            UserCalledCountControl.add(UserCalledCountControl.FUNCTIONS),
        ],
    )
)
async def harrow(app: Ariadne, group: Group, source: Source):
    await app.send_group_message(group, get_harrow(), quote=source)


def get_harrow() -> MessageChain:
    card, filename = get_random_harrow()
    content = f"{card['name']} （{card['name-en']}）[{card['deck']}] [{card['alignment']}] [{card['attribute']}]\n牌意：{card['meaning']}"
    elements = []
    img_path = Path.cwd() / "modules" / "third_party" / "harrow" / "card" / f"{filename}.jpg"
    if filename and img_path.exists():
        elements.append(Image(path=img_path))
    elements.append(content)
    return MessageChain(elements)


def get_random_harrow():
    path = Path().cwd() / "modules" / "third_party" / "harrow" / "card" / "harrow.json"
    with open(path, "r", encoding="utf-8") as json_file:
        data = json.load(json_file)
    decks = ["hammer", "key", "shield", "book", "star", "crown"]
    cards = []
    for deck in decks:
        cards.extend(data[deck])
    card = random.choice(cards)
    filename = "{}".format(card['num'])
    return card, filename

@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight([
                get_command(__file__, channel.module),
                UnionMatch("占卜"),
                UnionMatch("力量", "锤", "敏捷", "钥", "体质", "盾", "智力", "书", "感知", "星", "魅力", "冠") @ "choosing",
                WildcardMatch() @ "question"
            ])
        ],
        decorators=[
            Distribute.distribute(),
            FrequencyLimit.require("harrow", 1),
            Function.require(channel.module, notice=True),
            BlackListControl.enable(),
            UserCalledCountControl.add(UserCalledCountControl.FUNCTIONS),
        ],
    )
)
async def harrowing(app: Ariadne, group: Group, source: Source, choosing: RegexResult) -> MessageChain:
    dictionary = make_harrowing(choosing)
    path = Path().cwd() / "modules" / "third_party" / "harrow" / "template" / "spread.html"
    page_option = {"viewport": {"width": 750, "height": 10}, "device_scale_factor": 1.5}
    img = await template2img(path, dictionary, page_option)
    elements = []
    elements.append(Image(data_bytes=img))
    await app.send_group_message(group, MessageChain(elements), quote=source)

def make_harrowing(choosing: RegexResult):
    choosing = choosing.result.display
    if choosing == "力量" or choosing == "锤":
        deck = "hammer"
    elif choosing == "敏捷" or choosing == "钥":
        deck = "key"
    elif choosing == "体质" or choosing == "盾":
        deck = "shield"
    elif choosing == "智力" or choosing == "书":
        deck = "book"
    elif choosing == "感知" or choosing == "星":
        deck = "star"
    elif choosing == "魅力" or choosing == "冠":
        deck = "crown"
    else:
        deck = choosing
    path = Path().cwd() / "modules" / "third_party" / "harrow" / "card" / "harrow.json"
    with open(path, "r", encoding="utf-8") as json_file:
        data = json.load(json_file)
    cards = data[deck]
    chosen = random.choice(cards)
    dictionary = {}
    dictionary.update({"chosen": chosen})
    dictionary.update({"chosen_img": get_img(chosen)})
    decks = ["hammer", "key", "shield", "book", "star", "crown"]
    cards = []
    for deck in decks:
        cards.extend(data[deck])
    spread = random.sample(cards, 9)
    aligns = iter(["00", "01", "02", "10", "11", "12", "20", "21", "22"])
    matches = []
    images = []
    for card in spread:
        align = next(aligns)
        images.append(get_img(card))
        match = {}
        if card == chosen:
            match.update({"chosen":1})
        else:
            match.update({"chosen":0})
        if align == card["align"]:
            match.update({"align":1}) #True Match = 1
        elif int(align) + int(card["align"]) == 22 and align != card["align"]:
            match.update({"align":2}) #Opposite Match = 2
        elif align[0:1] == card["align"][0:1] or align[-1:] == card["align"][-1:]:
            match.update({"align":3}) #Partial Match = 3
        else:
            match.update({"align":0}) #No Match = 0
        if int(align[-1:]) + int(card["align"][-1:]) == 2 and align[-1:] != card["align"][-1:]:
            match.update({"misaligned":1})
        else:
            match.update({"misaligned":0})
        matches.append(match)
    dictionary.update({"matches": matches})
    dictionary.update({"spread": spread})
    dictionary.update({"images": images})
    return dictionary

@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight([
                get_command(__file__, channel.module),
                UnionMatch("占卜")
            ])
        ],
        decorators=[
            Distribute.distribute(),
            FrequencyLimit.require("harrow", 1),
            Function.require(channel.module, notice=True),
            BlackListControl.enable(),
            UserCalledCountControl.add(UserCalledCountControl.FUNCTIONS),
        ],
    )
)
async def harrowing_hint(app: Ariadne, group: Group, source: Source) -> MessageChain:
    content = "请在心中将你希望占卜的事物化作一个简单的问题，并选出一个最契合该问题的牌组：\n锤（力量）：战争、荣耀、残暴\n钥（敏捷）：孩童、危机、麻烦\n盾（体质）：健康、家园、疼痛\n书（智力）：金钱、秘密、故事\n星（感知）：信仰、道德、信任\n冠（魅力）：家庭、爱情、政治\n然后输入\"哈罗牌 占卜 [牌组名/属性名]\"\n\n在牌阵中，从左往右依次代表过去，现在，未来；从上往下依次代表积极面，中立面，消极面；牌阵同时也对应阵营的九宫格。\n解读时，应按照过去到未来的顺序，优先解读受选牌、阵营完全匹配的牌（蓝色的T）、阵营完全对立的牌（红色的O）；如果某个时间段内不存在这样的牌，则解读阵营部分匹配的牌；如果仍找不到，则自行选择一张进行解读。注意，如果一张牌处于异位（即善邪颠倒，标记为⟳），则需要按照异位牌意解读。"
    elements = []
    elements.append(content)
    await app.send_group_message(group, MessageChain(elements), quote=source)

@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight([
                get_command(__file__, channel.module)
            ])
        ],
        decorators=[
            Distribute.distribute(),
            FrequencyLimit.require("harrow", 1),
            Function.require(channel.module, notice=True),
            BlackListControl.enable(),
            UserCalledCountControl.add(UserCalledCountControl.FUNCTIONS),
        ],
    )
)
async def harrowing_guide(app: Ariadne, group: Group, source: Source) -> MessageChain:
    content = "抽一张哈罗牌，请输入'哈罗牌 抽卡'\n通过名字查找一张哈罗牌，请输入'哈罗牌 查看 [牌名]'\n进行一次完整的挂毯式哈罗占卜，请输入'哈罗牌 占卜 [牌组名/属性名]'"
    elements = []
    elements.append(content)
    await app.send_group_message(group, MessageChain(elements), quote=source)

@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight([
                get_command(__file__, channel.module),
                UnionMatch("查看"),
                WildcardMatch() @ "name"
            ])
        ],
        decorators=[
            Distribute.distribute(),
            FrequencyLimit.require("harrow", 1),
            Function.require(channel.module, notice=True),
            BlackListControl.enable(),
            UserCalledCountControl.add(UserCalledCountControl.FUNCTIONS),
        ],
    )
)

async def check_harrow(app: Ariadne, group: Group, source: Source, name: RegexResult):
    name = name.result.display
    await app.send_group_message(group, get_specific_harrow(name), quote=source)

def get_specific_harrow(name) -> MessageChain:
    path = Path().cwd() / "modules" / "third_party" / "harrow" / "card" / "harrow.json"
    with open(path, "r", encoding="utf-8") as json_file:
        data = json.load(json_file)
    decks = ["hammer", "key", "shield", "book", "star", "crown"]
    cards = []
    elements = []
    for deck in decks:
        cards.extend(data[deck])
    for card in cards:
        if name == card["name"] or name == card["name-en"]:
            content = f"{card['name']} （{card['name-en']}）[{card['deck']}] [{card['alignment']}] [{card['attribute']}]\n牌意：{card['meaning']}"
            filename = "{}".format(card['num'])
            img_path = Path.cwd() / "modules" / "third_party" / "harrow" / "card" / f"{filename}.jpg"
            if filename and img_path.exists():
                elements.append(Image(path=img_path))
            elements.append(content)
            return MessageChain(elements)
    content = "找不到这张牌哦~"
    elements.append(content)
    return MessageChain(elements)