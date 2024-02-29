CART_OPEN = '\U00013379'
CART_CLOSE = '\U0001337A'
BEGIN_ENCL = '\U0001343C'
END_ENCL = '\U0001343D'
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

N33 = '\U00013212'
N33a = '\U00013213'
N35 = '\U00013216'
N35a = '\U00013217'
V10 = '\U00013377'
Z1 = '\U000133E4'
Z2 = '\U000133E5'
Z3 = '\U000133EA'
Z4a = '\U000133EE'

class Horizontal:
	def __init__(self, groups):
		self.groups = groups

	def normalize(self):
		normals = [group.normalize() for group in self.groups]
		normals = group_triple(normals, N33, N33a)
		normals = group_triple(normals, Z1, Z2)
		normals = group_double(normals, Z1, Z4a)
		if len(normals) > 0:
			return Horizontal(normals)
		else:
			return normals[0]

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

	def normalize(self):
		normals = [group.normalize() for group in self.groups]
		normals = group_triple(normals, N35, N35a)
		normals = group_triple(normals, Z1, Z3)
		if len(normals) > 0:
			return Vertical(normals)
		else:
			return normals[0]

	def to_unicode(self):
		return VER.join([self.sub_expr(group) for group in self.groups])

	@staticmethod
	def sub_expr(group):
		return group.to_unicode()

class Cartouche:
	def __init__(self, groups):
		self.groups = groups

	def normalize(self):
		normals = [group.normalize() for group in self.groups]
		return Cartouche(normals)

	def to_unicode(self):
		contents = ''.join([group.to_unicode() for group in self.groups])
		return CART_OPEN + BEGIN_ENCL + contents + END_ENCL + CART_CLOSE

class Basic:
	def __init__(self, core):
		self.core = core
		self.corner_to_group = {}

	def normalize(self):
		if self.core == V10 and M in self.corner_to_group and \
				isinstance(self.corner_to_group[M], Horizontal):
			return Cartouche(self.corner_to_group[M].groups)
		else:
			return self

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

def group_triple(groups, unit, joint):
	i = 0
	while i+2 < len(groups):
		if isinstance(groups[i], Basic) and groups[i].core == unit and \
				isinstance(groups[i+1], Basic) and groups[i+1].core == unit and \
				isinstance(groups[i+2], Basic) and groups[i+2].core == unit:
			groups = groups[:i] + [Basic(joint)] + groups[i+3:]
		i += 1
	return groups

def group_double(groups, unit, joint):
	i = 0
	while i+1 < len(groups):
		if isinstance(groups[i], Basic) and groups[i].core == unit and \
				isinstance(groups[i+1], Basic) and groups[i+1].core == unit:
			groups = groups[:i] + [Basic(joint)] + groups[i+2:]
		i += 1
	return groups
