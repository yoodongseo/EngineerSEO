class FilterModule(object):
    def filters(self):
        return {
            'find_value': self.find_value
        }

    def find_value(self, value, delimiter, key):
        if not isinstance(value, str):
            raise TypeError('The first argument must be a string')
        if not isinstance(delimiter, str) or len(delimiter) != 1:
            raise ValueError('The second argument must be a single character string')
        if not isinstance(key, str):
            raise TypeError('The third argument must be a string')

        lines = value.splitlines()
        for line in lines:
            if line.strip().startswith(key + delimiter):
                _, found_value = line.split(delimiter, 1)
                # Remove leading/trailing spaces and quotes
                return found_value.strip().strip('"').strip("'")
        return None