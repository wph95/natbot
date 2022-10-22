black_listed_elements = set(
    ["html", "head", "title", "meta", "iframe", "body", "script", "style", "path", "svg", "br", "::marker", ])
# TODO
device_pixel_ratio = 2
anchor_ancestry = {"-1": (False, None)}
button_ancestry = {"-1": (False, None)}


class Node:
    def __init__(self):
        self.redundant = False
        self.is_clickable = None
        self.meta = []
        self.value = None
        self.name = None
        self.backend_node_id = None
        self.index = None
        self.black = False

        self.is_visible = False

        # if value == "|" or text == "•":
        self.special_char = False


        self.children = []

    def __dict__(self):
        return {
            "name": self.name,
            "value": self.value,
            "meta": self.meta,
            "is_clickable": self.is_clickable,
            "is_visible": self.is_visible,
        }

    def __str__(self):
        return f"{self.name} {self.value} {self.meta} {self.parent_id} {self.is_clickable} {self.is_visible}"

    @property
    def is_ignore_node(self):
        return self.name in black_listed_elements or self.black or self.special_char or self.redundant

    def set_visible(self, document, cursor):
        [x, y, width, height] = document.bounds[cursor]
        x /= device_pixel_ratio
        y /= device_pixel_ratio
        width /= device_pixel_ratio
        height /= device_pixel_ratio

        elem_left_bound = x
        elem_top_bound = y
        elem_right_bound = x + width
        elem_lower_bound = y + height


        self.origin_x= int(x)
        self.origin_y= int(y)
        self.center_x= int(x + (width / 2))
        self.center_y= int(y + (height / 2))


        self.is_visible = (
                elem_left_bound < document.win_right_bound
                and elem_right_bound >= document.win_left_bound
                and elem_top_bound < document.win_lower_bound
                and elem_lower_bound >= document.win_upper_bound
        )

    def set_meta(self, document):
        is_ancestor_of_anchor, anchor_id = document.add_to_hash_tree(
            anchor_ancestry, "a", self.index, self.name, self.parent_id
        )

        is_ancestor_of_button, button_id = document.add_to_hash_tree(
            button_ancestry, "button", self.index, self.name, self.parent_id
        )

        ancestor_exception = is_ancestor_of_anchor or is_ancestor_of_button

        ancestor_node = None
        if ancestor_exception:
            ancestor_node_key = None
            if is_ancestor_of_anchor:
                ancestor_node_key = str(anchor_id)
            elif is_ancestor_of_button:
                ancestor_node_key = str(button_id)
            ancestor_node = document.child_nodes.setdefault(str(ancestor_node_key), [])

        # inefficient to grab the same set of keys for kinds of objects but its fine for now
        element_attributes = document.find_attributes(
            document.attributes[self.index],
            ["type", "placeholder", "aria-label", "title", "alt"]
        )
        if self.name == "#text" and ancestor_exception:
            text = document.strings[document.node_value[self.index]]
            if text == "|" or text == "•":
                self.special_char = True

            ancestor_node.append({
                "type": "type", "value": text
            })
        else:
            if (
              self.name == "input" and element_attributes.get("type") == "submit"
            ) or self.name == "button":
                self.name = "button"
                element_attributes.pop(
                    "type", None
                )  # prevent [button ... (button)..]

            for key in element_attributes:
                if ancestor_exception:
                    ancestor_node.append({
                        "type": "attribute",
                        "key": key,
                        "value": element_attributes[key]
                    })
                else:
                    self.meta.append(element_attributes[key])
        # # remove redundant elements
        if ancestor_exception and (self.name != "a" and self.name != "button"):
            self.redundant = True

    def parse_node(self, document, index, node_name_index):
        self.parent_id = document.parent[index]
        self.name = document.strings[node_name_index].lower()
        self.origin_name = document.strings[node_name_index].lower()
        self.index = index

        try:
            cursor = document.layout_node_index.index(
                index
            )  # todo replace this with proper cursoring, ignoring the fact this is O(n^2) for the moment
        except:
            return None

        self.set_visible(document, cursor)
        self.set_meta(document)

        element_node_value = None

        if document.node_value[index] >= 0:
            element_node_value = document.strings[document.node_value[index]]
            if element_node_value == "|":  # commonly used as a seperator, does not add much context - lets save ourselves some token space
                self.special_char = True
        if (
                self.name == "input"
                and index in document.input_value_index
                and element_node_value is None
        ):
            node_input_text_index = document.input_value_index.index(index)
            text_index = document.input_value_values[node_input_text_index]
            if node_input_text_index >= 0 and text_index >= 0:
                element_node_value = document.strings[text_index]

        self.value = element_node_value
