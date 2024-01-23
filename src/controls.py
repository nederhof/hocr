VER = '\U00013430'
HOR = '\U00013431'
TS = '\U00013432'
BS = '\U00013433'
TE = '\U00013434'
BE = '\U00013435'
BEGIN = '\U00013437'
END = '\U00013438'
M = '\U00013439'
T = '\U0001343A'
B = '\U0001343B'
CORNERS = [TS, BS, TE, BE, M, T, B]

class Horizontal:
	def __init__(self, groups):
		self.groups = groups

	def to_unicode(self):
		return HOR.join([self.sub_expr(group) for group in self.groups])

	@staticmethod
	def sub_expr(group):
		if isinstance(group, Vertical):
			return BEGIN + group.to_unicode() + END
		else:
			return group.to_unicode()

class Vertical:
	def __init__(self, groups):
		self.groups = groups

	def to_unicode(self):
		return VER.join([self.sub_expr(group) for group in self.groups])

	@staticmethod
	def sub_expr(group):
		return group.to_unicode()

class Basic:
	def __init__(self, core):
		self.core = core
		self.corner_to_group = {}

	def to_unicode(self):
		s = self.core
		for corner in CORNERS:
			if corner in self.corner_to_group:
				s += corner + self.sub_expr(self.corner_to_group[corner])
		return s

	def has_insertions(self):
		return len(self.corner_to_group) > 0
	
	@staticmethod
	def sub_expr(group):
		if isinstance(group, Basic) and not group.has_insertions():
			return group.to_unicode()
		else:
			return BEGIN + group.to_unicode() + END
