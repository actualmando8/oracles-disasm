; ==================================================================================================
; INTERAC_ROSA_HIDING
; ==================================================================================================
interactionCode6c:
	ld e,Interaction.subid
	ld a,(de)
	rst_jumpTable
	.dw rosaSubId0
	.dw rosaSubId1

; ==================================================================================================
; INTERAC_STRANGE_BROTHERS_HIDING
; ==================================================================================================
interactionCode6d:
	ld e,Interaction.subid
	ld a,(de)
	rst_jumpTable
	.dw strangeBrothersSubId0
	.dw strangeBrothersSubId1
	.dw strangeBrothersSubId2

rosaSubId0:
	ld e,Interaction.substate
	ld a,(de)
	rst_jumpTable
	.dw @substate0
	.dw @substate1
@substate0:
	ld a,$01
	ld (de),a
	ld a,TREASURE_ESSENCE
	call checkTreasureObtained
	and $01
	jp z,interactionDelete
	call getThisRoomFlags
	bit 7,a
	jp nz,interactionDelete
	call interactionSetAlwaysUpdateBit
	call objectSetReservedBit1
	ld a,$01
	ld (wDisabledObjects),a
	ld (wMenuDisabled),a
	ld e,$79
	ld a,(wActiveRoom)
	ld (de),a
	xor a
	ld (wActiveMusic),a
	ld a,$0b
	call playSound
@func_67d1:
	ld a,$80
	ld (wcc85),a
	ld a,$01
	ld (wDisableScreenTransitions),a
	ldbc $01 INTERAC_ROSA_HIDING
	call spawnHider
	ld e,a
	ld bc,@table_67f1
	call addDoubleIndexToBc
	call func_69ac
	ld a,e
	cp $04
	jr z,@func_680c
	ret
@table_67f1:
	; yh - xh
	.db $28 $50
	.db $58 $68
	.db $58 $58
	.db $58 $58
	.db $58 $58
@func_67fb:
	ld a,(wActiveRoom)
	cp $cb
	jp z,interactionDelete
	ld a,(wActiveMusic2)
	ld (wActiveMusic),a
	call playSound
@func_680c:
	xor a
	ld (wcc85),a
	ld (wDisableScreenTransitions),a
	jp interactionDelete
@substate1:
	ld e,$78
	ld a,(de)
	rst_jumpTable
	.dw @var38_00
	.dw @var38_01
@var38_00:
	ld a,(wActiveRoom)
	cp $cb
	jr nz,@func_67fb
	ld a,(wcc84)
	cp $02
	ret nz
	ld e,$78
	ld a,$01
	ld (de),a
	ret
@var38_01:
	ld a,(wTmpcfc0.genericCutscene.state)
	or a
	jr z,+
	ld e,$7a
	ld a,$01
	ld (de),a
	xor a
	ld (wDisableScreenTransitions),a
+
	ld e,$79
	ld a,(de)
	ld b,a
	ld a,(wActiveRoom)
	cp b
	ret z
	ld (de),a
	cp $cb
	jr z,@func_67fb
	ld e,$7a
	ld a,(de)
	or a
	jr z,@func_67fb
	xor a
	ld (de),a
	ld h,d
	ld l,$46
	inc (hl)
	ld a,(hl)
	ld bc,@table_686c
	call addAToBc
	ld a,(bc)
	ld b,a
	ld a,(wActiveRoom)
	cp b
	jr nz,@func_67fb
	jp @func_67d1
@table_686c:
	.db $cb $bb $ab $9b $9a

rosaSubId1:
	ld e,Interaction.substate
	ld a,(de)
	rst_jumpTable
	.dw @substate0
	.dw @substate1
	.dw @substate2
	.dw @substate3
	.dw @substate4
	.dw @substate5
@substate0:
	ld a,$01
	ld (de),a
	call interactionInitGraphics
	ld e,$43
	ld a,(de)
	ld hl,table_6931
	rst_addDoubleIndex
	ldi a,(hl)
	ld h,(hl)
	ld l,a
	call interactionSetScript
	ld e,$6d
	ld a,$08
	ld (de),a
	call objectSetVisiblec2
@substate1:
	call interactionRunScript
	jp c,interactionDelete
@func_68a2:
	ld c,$20
	jp objectUpdateSpeedZ_paramC
@substate2:
	call interactionRunScript
	jp c,interactionDelete
	ld c,$20
	call objectUpdateSpeedZ_paramC
	ret nz
	ld bc,$fe40
	jp objectSetSpeedZ
@substate3:
	call interactionAnimate
	call @func_68a2
	ret nz
	call interactionRunScript
	jp c,interactionDelete
	ret
@substate4:
	ld e,$7b
	ld a,(de)
	inc a
	jr z,+
	jr @substate3
+
	ld hl,mainScripts.rosaHidingScript_caught
	call interactionSetScript
	jp interactionRunScript
@substate5:
	call interactionAnimate
	call @func_68a2
	ret nz
	ld a,$09
	call objectGetShortPosition_withYOffset
	ld c,a
	ld b,$ce
	ld a,(bc)
	cp $ff
	jr z,+
	or a
	jr nz,++
+
	ld a,$10
	jr func_6919
++
	ld e,$6d
	ld a,(de)
	ldh (<hFF8B),a
	ld e,$49
	ld (de),a
	call convertAngleDeToDirection
	xor $02
	sub $02
	add c
	ld c,a
	ld a,(bc)
	or a
	ldh a,(<hFF8B)
	jr z,func_6919
	ld e,$6d
	ld a,(de)
	cp $08
	jr z,+
	ld a,$08
	ld (de),a
	jr func_6919
+
	ld a,$18
	ld (de),a
func_6919:
	ld e,$49
	ld (de),a
	call objectApplySpeed
	ld e,$4b
	ld a,(de)
	cp $90
	jr nc,+
	ret
+
	xor a
	ld (wDisabledObjects),a
	ld (wDisableScreenTransitions),a
	jp interactionDelete
table_6931:
	.dw mainScripts.rosaHidingScript_1stScreen
	.dw mainScripts.rosaHidingScript_2ndScreen
	.dw mainScripts.rosaHidingScript_3rdScreen
	.dw mainScripts.rosaHidingScript_4thScreen
	.dw mainScripts.rosaHidingScript_portalScreen
	.dw mainScripts.rosaHidingScript_caught

strangeBrothersSubId0:
	ld e,Interaction.state
	ld a,(de)
	rst_jumpTable
	.dw @state0
	.dw strangeBrothersSubId0State1
	.dw strangeBrothersSubId0State2
	.dw strangeBrothersSubId0State3
@state0:
	ld a,$01
	ld (de),a
	ld a,GLOBALFLAG_STRANGE_BROTHERS_HIDING_IN_PROGRESS
	call checkGlobalFlag
	jp nz,interactionDelete
	ld e,$40
	ld a,$83
	ld (de),a
	ld a,(wActiveRoom)
	ld (wTmpcfc0.genericCutscene.cfd0+1),a
	ld a,GLOBALFLAG_STRANGE_BROTHERS_HIDING_IN_PROGRESS
	call setGlobalFlag
func_6964:
	ld a,$01
	ld (wDisableScreenTransitions),a
	ldbc $01 INTERAC_STRANGE_BROTHERS_HIDING
	call spawnHider
	ldbc $02 INTERAC_STRANGE_BROTHERS_HIDING
	call spawnHider
	ld a,TREASURE_FEATHER
	call checkTreasureObtained
	ld a,$01
	jr nc,+
	call getRandomNumber
	and $01
+
	ld (wTmpcfc0.genericCutscene.cfd0),a
	ld e,$46
	ld a,(de)
	cp $06
	jp z,func_6995
	ret
func_698f:
	ld a,(wActiveMusic)
	call playSound
func_6995:
	xor a
	ld (wcc84),a
	jp interactionDelete

;;
; @param[out]	b	subid
; @param[out]	c	id
spawnHider:
	call getFreeInteractionSlot
	dec l
	set 7,(hl)
	inc l
	ld (hl),c
	inc l
	ld (hl),b
	inc l
	ld e,$46
	ld a,(de)
	ld (hl),a
	ret

func_69ac:
	ld l,$4b
	ld a,(bc)
	ldi (hl),a
	inc l
	inc bc
	ld a,(bc)
	ld (hl),a
	ret

strangeBrothersSubId0State1:
	ld a,(wScrollMode)
	and $01
	ret z
	ld a,(wcc84)
	cp $02
	ret nz
	xor a
	ld (wTmpcfc0.genericCutscene.state),a
	ld e,Interaction.state
	ld a,$02
	ld (de),a
	ld a,GLOBALFLAG_JUST_CAUGHT_BY_STRANGE_BROTHERS
	call unsetGlobalFlag
	ld a,$0b
	jp playSound

strangeBrothersSubId0State2:
	ld a,(wTmpcfc0.genericCutscene.state)
	cp $ff
	jr z,func_6a23
	and $03
	cp $03
	jr nz,+
	ld e,$7a
	ld (de),a
	xor a
	ld (wDisableScreenTransitions),a
	ld (wTmpcfc0.genericCutscene.state),a
+
	ld a,(wActiveRoom)
	ld b,a
	ld a,(wTmpcfc0.genericCutscene.cfd0+1)
	cp b
	ret z
	ld a,b
	ld (wTmpcfc0.genericCutscene.cfd0+1),a
	cp $51
	jr z,func_698f
	ld e,$7a
	ld a,(de)
	cp $03
	jr nz,func_698f
	xor a
	ld (de),a
	ld h,d
	ld l,$46
	inc (hl)
	ld a,(hl)
	ld bc,@table_6a1c
	call addAToBc
	ld a,(bc)
	ld b,a
	ld a,(wActiveRoom)
	cp b
	jp nz,func_698f
	jp func_6964
@table_6a1c:
	.db $51 $61 $71 $70
	.db $60 $50 $60
func_6a23:
	ld e,Interaction.state
	ld a,$03
	ld (de),a
	ld a,$01
	ld (wMenuDisabled),a
	ld bc,TX_2804
	jp showText

strangeBrothersSubId0State3:
	ld a,(wTmpcfc0.genericCutscene.state)
	or a
	ret nz
	ld a,GLOBALFLAG_JUST_CAUGHT_BY_STRANGE_BROTHERS
	call setGlobalFlag
	ld a,GLOBALFLAG_STRANGE_BROTHERS_HIDING_IN_PROGRESS
	call unsetGlobalFlag
	xor a
	ld (wDisableScreenTransitions),a
	ld hl,@warpDestVariables
	call setWarpDestVariables
	jp interactionDelete
@warpDestVariables:
	m_HardcodedWarpA ROOM_SEASONS_151 $00 $28 $03

strangeBrothersSubId1:
strangeBrothersSubId2:
	ld e,Interaction.state
	ld a,(de)
	rst_jumpTable
	.dw @state0
	.dw @state1
	.dw @state2
@state0:
	ld a,$01
	ld (de),a
	call interactionInitGraphics
	ld e,$50
	ld a,$28
	ld (de),a
	ld e,Interaction.subid
	ld a,(de)
	ld b,a
	dec a
	ld a,$02
	jr z,+
	dec a
+
	ld e,$5c
	ld (de),a
	ld a,b
	dec a
	ld hl,@table_6a92
	rst_addDoubleIndex
	ldi a,(hl)
	ld h,(hl)
	ld l,a
	ld e,$43
	ld a,(de)
	rst_addDoubleIndex
	ldi a,(hl)
	ld h,(hl)
	ld l,a
	call interactionSetScript
	call interactionRunScript
	call interactionRunScript
	jp objectSetVisiblec2
@table_6a92:
	.dw @table_6a96
	.dw @table_6aa4
@table_6a96:
	.dw mainScripts.strangeBrother1Script_1stScreen
	.dw mainScripts.strangeBrother1Script_2ndScreen
	.dw mainScripts.strangeBrother1Script_3rdScreen
	.dw mainScripts.strangeBrother1Script_4thScreen
	.dw mainScripts.strangeBrother1Script_5thScreen
	.dw mainScripts.strangeBrother1Script_6thScreen
	.dw mainScripts.strangeBrother1Script_finishedScreen
@table_6aa4:
	.dw mainScripts.strangeBrother2Script_1stScreen
	.dw mainScripts.strangeBrother2Script_2ndScreen
	.dw mainScripts.strangeBrother2Script_3rdScreen
	.dw mainScripts.strangeBrother2Script_4thScreen
	.dw mainScripts.strangeBrother2Script_5thScreen
	.dw mainScripts.strangeBrother2Script_6thScreen
	.dw mainScripts.strangeBrother2Script_finishedScreen
@state1:
	ld a,(wLinkPlayingInstrument)
	or a
	jr nz,@func_6add
	ld e,$7b
	ld a,(de)
	or a
	jr nz,@func_6add
	ld a,(wTmpcfc0.genericCutscene.state)
	cp $ff
	jr z,@func_6add
	call interactionAnimate
	call interactionAnimate
	call interactionRunScript
	jp c,interactionDelete
@func_6ad1:
	ld c,$60
	call objectUpdateSpeedZ_paramC
	ret nz
	ld bc,$fe00
	jp objectSetSpeedZ
@func_6add:
	ld a,$ff
	ld (wTmpcfc0.genericCutscene.state),a
	ld a,$01
	ld (wDisabledObjects),a
	ld h,d
	ld l,$44
	inc (hl)
	ld l,$50
	ld (hl),$64
	call objectGetAngleTowardLink
	add $10
	and $1f
	ld e,$49
	ld (de),a
	call convertAngleDeToDirection
	jp interactionSetAnimation
@state2:
	call interactionAnimate
	call interactionAnimate
	call @func_6ad1
	call retIfTextIsActive
	call objectApplySpeed
	call objectCheckWithinScreenBoundary
	ret c
	call objectSetInvisible
	ld h,d
	ld l,$44
	inc (hl)
	jr +
+
	xor a
	ld (wTmpcfc0.genericCutscene.state),a
	jp interactionDelete
