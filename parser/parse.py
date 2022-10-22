from typing import List

from Node import Node

class Document:
    def __init__(self, document, strings, win_right_bound, win_left_bound, win_lower_bound, win_upper_bound):
        self.document = document
        self.strings = strings
        self.nodes = self.document["nodes"]
        self.node_names = self.nodes["nodeName"]
        self.parent = self.nodes["parentIndex"]
        self.win_right_bound = win_right_bound
        self.win_left_bound = win_left_bound
        self.win_lower_bound = win_lower_bound
        self.win_upper_bound = win_upper_bound

        self.layout = self.document["layout"]
        self.layout_node_index = self.layout["nodeIndex"]
        self.bounds = self.layout["bounds"]
        self.attributes = self.nodes["attributes"]
        self.node_value = self.nodes["nodeValue"]

        self.child_nodes = {}

        input_value = self.nodes["inputValue"]
        self.input_value_index = input_value["index"]
        self.input_value_values = input_value["value"]
        self.backend_node_id = self.nodes["backendNodeId"]
        self.is_clickable = set(self.nodes["isClickable"]["index"])

    def to_nodes(self):
        results = []

        for index, node_name_index in enumerate(self.node_names):

            node = self.parse_node(index, node_name_index)

            if node is not None:
                results.append(node)

        return results

    def parse_node(self, index, node_name_index):
        node = Node()
        node.parse_node(document=self, index=index, node_name_index=node_name_index)
        return node



    def convert_name(self, node_name, has_click_handler):
        if node_name == "a":
            return "link"
        if node_name == "input":
            return "input"
        if node_name == "img":
            return "img"
        if (
                node_name == "button" or has_click_handler
        ):  # found pages that needed this quirk
            return "button"
        else:
            return "text"

    def find_attributes(self, attributes, keys):
        values = {}

        for [key_index, value_index] in zip(*(iter(attributes),) * 2):
            if value_index < 0:
                continue
            key = self.strings[key_index]
            value = self.strings[value_index]

            if key in keys:
                values[key] = value
                keys.remove(key)

                if not keys:
                    return values

        return values

    def add_to_hash_tree(self, hash_tree, tag, node_id, node_name, parent_id):
        parent_id_str = str(parent_id)
        if not parent_id_str in hash_tree:
            parent_name = self.strings[self.node_names[parent_id]].lower()
            grand_parent_id = self.parent[parent_id]

            self.add_to_hash_tree(
                hash_tree, tag, parent_id, parent_name, grand_parent_id
            )

        is_parent_desc_anchor, anchor_id = hash_tree[parent_id_str]

        # even if the anchor is nested in another anchor, we set the "root" for all descendants to be ::Self
        if node_name == tag:
            value = (True, node_id)
        elif (
                is_parent_desc_anchor
        ):  # reuse the parent's anchor_id (which could be much higher in the tree)
            value = (True, anchor_id)
        else:
            value = (
                False,
                None,
            )  # not a descendant of an anchor, most likely it will become text, an interactive element or discarded

        hash_tree[str(node_id)] = value

        return value

    def get_interest_node(self, nodes: List[Node]):
        elements_of_interest = {}
        id_counter = 0

        nodesMap = {}
        for node in nodes:
            nodesMap[node.index] = node

        for node in nodes:
            if node.parent_id > 0:
                parent = nodesMap.get(node.parent_id)
                if parent:
                    parent.children.append(node)

        for node in nodes:
            if node.is_ignore_node:
                continue
            inner_text = f"{node.value} " if node.value else ""
            meta = ""

            # TODO, move it to parse_node
            if node.index in self.child_nodes:
                for child in self.child_nodes.get(node.index):
                    entry_type = child.get('type')
                    entry_value = child.get('value')

                    if entry_type == "attribute":
                        entry_key = child.get('key')
                        node.meta.append(f'{entry_key}="{entry_value}"')
                    else:
                        inner_text += f"{entry_value} "

            if node.meta:
                meta_string = " ".join(node.meta)
                meta = f" {meta_string}"

            if inner_text != "":
                inner_text = f"{inner_text.strip()}"

            converted_node_name = self.convert_name(node.name, node.is_clickable)

            # not very elegant, more like a placeholder
            if (
                    (converted_node_name != "button" or meta == "")
                    and converted_node_name != "link"
                    and converted_node_name != "input"
                    and converted_node_name != "img"
                    and converted_node_name != "textarea"
            ) and inner_text.strip() == "":
                continue

            if inner_text != "":
                elements_of_interest[id_counter] = {
                    "id_counter": id_counter,
                    "type": converted_node_name,
                    "value": inner_text,
                    "meta": meta,
                    #  f"""<{converted_node_name} id={id_counter}{meta}>{inner_text}</{converted_node_name}>"""
                    "str": f"""<{converted_node_name} id={id_counter}{meta}>{inner_text}</{converted_node_name}>""",
                    "node": node
                }
            else:
                elements_of_interest[id_counter] = {
                    "id_counter": id_counter,
                    "type": converted_node_name,
                    "value": "",
                    "meta": meta,
                    "str": f"""<{converted_node_name} id={id_counter}{meta}/>""",
                    "node": node
                }

            id_counter += 1

        return elements_of_interest

    def range_tree(self, node: Node, is_read_list, level=0, out=None):
        if node.index in is_read_list:
            return
        is_read_list.append(node.index)
        content = ""

        # if node.value:
        #     out(node.value)
        for child in node.children:
            if child.value:
                content += f"{child.value} "

        content = content.strip()
        if len(content)>0:
            out.append("|" + level*"_" + content)
        for child in node.children:
            self.range_tree(child, is_read_list, level + 1, out)

    def list_intreset_node(self, en):
        results = []
        for node in en:
            results.append(node.get("str"))

