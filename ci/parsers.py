from xml.etree import ElementTree


class XunitParser(object):
    def __init__(self, content):
        self.content = content
        self.xml = ElementTree.fromstring(content)
        self.summary = self.xml.attrib
        for key in self.summary:
            if self.summary[key].isdigit():
                self.summary[key] = int(self.summary[key])

        self.testcases = []
        for testcase in self.xml:
            text = ''
            if len(testcase) == 1:  # Failure or error
                child = testcase[0]
                text = child.text
                status = child.tag
            elif len(testcase) == 0:  # Success
                status = 'success'
            attrs = testcase.attrib
            attrs.update({
                'status': status,
                # XXX python unittest doesn't seem to output newlines,
                # this reconstructs a somewhat readable ouput.
                'text': text.replace('  ', '\n  ').replace('\n  \n  ',
                                                           '\n    '),
            })
            if 'name' in attrs:
                self.testcases.append(attrs)
