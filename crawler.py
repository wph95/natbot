import asyncio

from playwright.async_api import Page

DEFAULT_WAIT_TIME = 5

class Session:
    def __init__(self, page: Page):
        self.page = page
        self.wait_load = DEFAULT_WAIT_TIME

    async def goto(self, url):
        await self.page.goto(url)
        self.client = await self.page.context.new_cdp_session(self.page)
        self.html = await self.html2text()

    async def html2text(self):
        win_upper_bound = await self.page.evaluate("window.pageYOffset")
        win_left_bound = await self.page.evaluate("window.pageXOffset")
        win_width = await self.page.evaluate("window.screen.width")
        win_height = await self.page.evaluate("window.screen.height")
        win_right_bound = win_left_bound + win_width
        win_lower_bound = win_upper_bound + win_height

        tree = await self.client.send(
            "DOMSnapshot.captureSnapshot",
            {"computedStyles": [], "includeDOMRects": True, "includePaintOrder": True},
        )
        strings = tree["strings"]
        document = tree["documents"][0]

        document = Document(document, strings, win_right_bound, win_left_bound, win_lower_bound, win_upper_bound)
        nodes = document.to_nodes()
        inodes = document.get_interest_node(nodes)
        is_read_list = []
        content = []

        # todo move it to outside
        self.intrerest_node = document.get_interest_node(nodes)

        for node in nodes:
            document.range_tree(node, is_read_list, 0, content)
        return content

    def show(self):
        print("==HTML TO TEXT===================================")
        print("\n".join(self.html))
        print("=================================================")
        print()
        print("==Interactable element=================================")
        print("\n".join([node.get("str") for node in self.intrerest_node.values()]))

    async def click(self, id):
        await self._click(id)
        await asyncio.sleep(self.wait_load)
        self.html = await self.html2text()

    async def _click(self, id):
        js = """
            		links = document.getElementsByTagName("a");
            		for (var i = 0; i < links.length; i++) {
            			links[i].removeAttribute("target");
            		}
            		"""
        await self.page.evaluate(js)
        v = self.intrerest_node[int(id)]["node"]
        await self.page.mouse.click(v.center_x, v.center_y)

    async def type(self, id, text):
        await self._click(id)
        await self.page.keyboard.type(text)
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(self.wait_load)
        self.html = await self.html2text()