class FilterModule(object):
    def filters(self):
        return {
            'sum_size': self.sum_size
        }

    def sum_size(self, value, type):
            if not isinstance(value, str):
                raise TypeError('Input must be a string')
            if not isinstance(type, str):
                raise TypeError('type must be a string')

            # Split the input string by lines
            lines = value.strip().split('\n')

            # Initialize total size
            total_size = 0

            # Iterate through each line starting from the second line (skip the header)
            for line in lines[1:]:
                # Split the line by spaces while preserving multiple spaces (to handle "Mounted on")
                parts = line.split()

                if len(parts) >= 2:
                    used_str = parts[1]
                    if type == 'disk':
                        # Remove any non-numeric characters from the end
                        if used_str[-1].isalpha():
                            unit = used_str[-1]
                            used_str = used_str[:-1]
                        else:
                            unit = ''

                        # Convert the string to a number
                        try:
                            used_value = float(used_str)
                        except ValueError:
                            continue

                        # # Convert to GB if the unit is 'M'
                        # if unit == 'G':
                        #     used_value *= 1024

                        total_size += used_value
                    else:
                        # Remove any non-numeric characters from the end
                        if used_str[-1].isalpha():
                            unit = used_str[-2:] if used_str[-2:].isalpha() else used_str[-1]
                            used_str = used_str[:-len(unit)]
                        else:
                            unit = ''

                        # Convert the string to a number
                        try:
                            used_value = float(used_str)
                        except ValueError:
                            continue

                        # # Convert to GB if the unit is 'Mi'
                        # if unit == 'G':
                        #     used_value *= 1024

                        total_size += used_value

            # Round the total size to one decimal place
            total_size = round(total_size, 1)

            return total_size
