from itertools import izip

from numpy import (array, zeros, arange, concatenate, searchsorted, where,
                   unique, cross, asarray)
from numpy.linalg import norm

from pyNastran.bdf.dev_vectorized.cards.elements.shell.shell_element import ShellElement
from .ctria3 import _ctria3_normal_A

from pyNastran.bdf.fieldWriter import print_card_8
from pyNastran.bdf.bdfInterface.assign_type import (integer, integer_or_blank,
    double_or_blank, integer_double_or_blank, blank)

class CTRIA6(ShellElement):
    type = 'CTRIA6'
    op2_id = 74
    def __init__(self, model):
        ShellElement.__init__(self, model)

    def build(self):
        cards = self._cards
        ncards = len(cards)
        self.n = ncards
        if ncards:
            ctria6
            float_fmt = self.model.float
            #: Element ID
            self.element_id = zeros(ncards, 'int32')
            #: Property ID
            self.property_id = zeros(ncards, 'int32')
            #: Node IDs
            self.node_ids = zeros((ncards, 6), 'int32')

            self.zoffset = zeros(ncards, 'int32')
            self.t_flag = zeros(ncards, 'int32')
            self.thickness = zeros((ncards, 3), float_fmt)

            for i, card in enumerate(cards):
                self.element_id[i] = integer(card, 1, 'element_id')

                self.property_id[i] = integer(card, 2, 'property_id')

                self.node_ids[i] = [
                    integer(card, 3, 'n1'),
                    integer(card, 4, 'n2'),
                    integer(card, 5, 'n3'),
                    integer_or_blank(card, 6, 'n4', 0),
                    integer_or_blank(card, 7, 'n5', 0),
                    integer_or_blank(card, 8, 'n6', 0)]

                #self.thetaMcid[i] = integer_double_or_blank(card, 9, 'thetaMcid', 0.0)
                self.zOffset[i] = double_or_blank(card, 10, 'zOffset', 0.0)

                self.thickness[i] = [
                    double_or_blank(card, 11, 'T1', 1.0),
                    double_or_blank(card, 12, 'T2', 1.0),
                    double_or_blank(card, 13, 'T3', 1.0), ]
                self.t_flag[i] = integer_or_blank(card, 14, 'TFlag', 0)
                assert len(card) <= 15, 'len(CTRIA6 card) = %i' % len(card)

            i = self.element_id.argsort()
            self.element_id = self.element_id[i]
            self.property_id = self.property_id[i]
            self.node_ids = self.node_ids[i, :]
            self.thicknes = self.thickness[i, :]
            self.t_flag = self.t_flag[i]
            self._cards = []
            self._comments = []
        else:
            self.element_id = array([], 'int32')
            self.property_id = array([], dtype='int32')

    def write_bdf(self, f, size=8, element_ids=None):
        if self.n:
            if element_ids is None:
                i = arange(self.n)
            else:
                assert len(unique(element_ids))==len(element_ids), unique(element_ids)
                i = searchsorted(self.element_id, element_ids)
            for (eid, pid, n, zoffset, t_flag, thickness) in izip(
                self.element_id[i], self.property_id[i], self.node_ids[i],
                self.zoffset[i], self.t_flag[i], self.thickness[i]):
                thetaMcid = None
                #TFlag = None
                card = ['CTRIA6', eid, pid, ] + list(n) + [thetaMcid, zOffset,
                        None] + [None, TFlag] + list(t)
                f.write(print_card_8(card))

    def _verify(self):
        self.get_mass()
        self.get_area()
        self.get_normal()

    def rebuild(self):
        pass

    def _node_locations(self, xyz_cid0, i=None):
        if xyz_cid0 is None:
            xyz_cid0 = self.model.grid.get_positions()
        if i is None:
            n1 = xyz_cid0[self.model.grid.index_map(self.node_ids[:, 0]), :]
            n2 = xyz_cid0[self.model.grid.index_map(self.node_ids[:, 1]), :]
            n3 = xyz_cid0[self.model.grid.index_map(self.node_ids[:, 2]), :]
        else:
            n1 = xyz_cid0[self.model.grid.index_map(self.node_ids[i, 0]), :]
            n2 = xyz_cid0[self.model.grid.index_map(self.node_ids[i, 1]), :]
            n3 = xyz_cid0[self.model.grid.index_map(self.node_ids[i, 2]), :]
        return n1, n2, n3

    def _mass_area_normal(self, element_ids=None, xyz_cid0=None,
                          calculate_mass=True, calculate_area=True,
                          calculate_normal=True):
        """
        Gets the mass, area, and normals of the CTRIA6s on a per
        element basis.

        :param self: the CTRIA6 object
        :param element_ids: the elements to consider (default=None -> all)

        :param node_ids: the GRIDs as an (N, )  NDARRAY (or None)
        :param xyz_cid0: the GRIDs as an (N, 3) NDARRAY in CORD2R=0 (or None)

        :param calculate_mass: should the mass be calculated (default=True)
        :param calculate_area: should the area be calculated (default=True)
        :param calculate_normal: should the normals be calculated (default=True)
        """
        if element_ids is None:
            element_ids = self.element_id
            property_id = self.property_id
            i = None
        else:
            i = searchsorted(self.element_id, element_ids)
            property_id = self.property_id[i]

        n1, n2, n3 = self._node_locations(xyz_cid0)
        if calculate_mass:
            calculate_area = True
        normal, A = _ctria3_normal_A(n1, n2, n3, calculate_area=calculate_area, normalize=True)

        massi = None
        if calculate_mass:
            mpa = self.model.properties_shell.get_mass_per_area(property_id)
            assert mpa is not None
            #massi = rho * A * t + nsm
            massi = mpa * A
        return massi, A, normal

    def _positions(self, nids_to_get, node_ids, grids_cid0):
        """
        Gets the positions of a list of nodes

        :param nids_to_get:  the node IDs to get as an NDARRAY
        :param node_ids:     the node IDs that contains all the nids_to_get
                             as an NDARRAY
        :param grids_cid_0:  the GRIDs as an (N, )  NDARRAY

        :returns grids2_cid_0 : the corresponding positins of the requested
                                GRIDs
        """
        grids2_cid_0 = grids_cid0[searchsorted(nids_to_get, node_ids), :]
        return grids2_cid_0

    def get_centroid(self, element_ids=None, node_ids=None, xyz_cid0=None):
        if element_ids is None:
            element_ids = self.element_id
            i = None
        else:
            i = searchsorted(self.element_id, element_ids)
        n1, n2, n3 = self._node_locations(xyz_cid0, i)
        return (n1 + n2 + n3) / 3.

    #def slice_by_index(self, i):
        #i = asarray(i)
        #obj = CTRIA6(self.model)
        #obj.n = len(i)
        ##obj._cards = self._cards[i]
        ##obj._comments = obj._comments[i]
        ##obj.comments = obj.comments[i]
        #obj.element_id = self.element_id[i]
        #obj.property_id = self.property_id[i]
        #obj.node_ids = self.node_ids[i, :]
        #obj.zoffset = self.zoffset[i]
        #obj.t_flag = self.t_flag[i]
        #obj.thickness = self.thickness[i, :]
        #return obj

