from pyteal import Bytes, Concat, Expr, abi, Btoi
import pyteal as pt

from beaker import consts
from algosdk import account
from algosdk.abi import ABIType
from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.encoding import decode_address, encode_address
from algosdk.transaction import AssetOptInTxn, PaymentTxn
from beaker.decorators import Authorize

from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
)

from beaker import *
from beaker.lib.storage import BoxList, BoxMapping
from beaker import (
    Application,
    client,
    sandbox,
)


class Item(pt.abi.NamedTuple): 
    sku: pt.abi.Field[pt.abi.Uint64]
    upc: pt.abi.Field[pt.abi.Uint64]
    ownerID: pt.abi.Field[pt.abi.Address]
    farmerID: pt.abi.Field[pt.abi.Address]
    farmName: pt.abi.Field[pt.abi.String]
    farmInformation: pt.abi.Field[pt.abi.String]
    farmLongitude: pt.abi.Field[pt.abi.String]
    farmLatitude: pt.abi.Field[pt.abi.String]
    productID: pt.abi.Field[pt.abi.Uint64]
    productNotes: pt.abi.Field[pt.abi.String]
    productPrice: pt.abi.Field[pt.abi.Uint64]
    itemState: pt.abi.Field[pt.abi.String]
    distributorID: pt.abi.Field[pt.abi.Address]
    retailerID: pt.abi.Field[pt.abi.Address]
    consumerID: pt.abi.Field[pt.abi.Address]

class SupplyChainState: 
    sku = GlobalStateValue(
        stack_type=pt.TealType.uint64, default=pt.Int(1)
    )

    farmer = GlobalStateValue(
        stack_type=pt.TealType.bytes, default=pt.Bytes("")
    )

    retailer = GlobalStateValue(
        stack_type=pt.TealType.bytes, default=pt.Bytes("")
    )

    distributor = GlobalStateValue(
        stack_type=pt.TealType.bytes, default=pt.Bytes("")
    )

    consumer = GlobalStateValue(
        stack_type=pt.TealType.bytes, default=pt.Bytes("")
    )

    def __init__(self):
        self.items = BoxMapping(pt.abi.Uint64, Item)

supply_chain_app = (
    Application(
    "SupplyChain",
    state=SupplyChainState(), 
    build_options=BuildOptions(scratch_slots=False),
).apply(unconditional_create_approval, initialize_global_state=True)
)

@supply_chain_app.external
def get_item(upc: pt.abi.Uint64, *, output:Item) -> Expr:
    return supply_chain_app.state.items[upc].store_into(output)

@supply_chain_app.external
def init_roles(upc: pt.abi.Uint64, farmerAddress: pt.abi.Address, distributorAddress: pt.abi.Address, retailerAddress: pt.abi.Address, consumerAddress: pt.abi.Address, *, output: pt.abi.Uint8) -> pt.Expr:
    return pt.Seq(
        supply_chain_app.state.farmer.set(farmerAddress.get()),
        supply_chain_app.state.retailer.set(retailerAddress.get()),
        supply_chain_app.state.distributor.set(distributorAddress.get()),
        supply_chain_app.state.consumer.set(consumerAddress.get()),
        output.set(supply_chain_app.state.sku)
    )
@supply_chain_app.external(authorize=Authorize.only(supply_chain_app.state.farmer))
def harvest_item(upc: pt.abi.Uint64, 
                 farmerAddress: pt.abi.Address, 
                 farmName: pt.abi.String, 
                 farmInformation: pt.abi.String,
                 farmLongitude: pt.abi.String,
                 farmLatitude: pt.abi.String, 
                 productNotes: pt.abi.String,
                 zeroAddress: pt.abi.Address,
                 *,
                 output: pt.abi.Uint64
                 ) -> pt.Expr:
    return pt.Seq(
        (sku := pt.abi.Uint64()).set(supply_chain_app.state.sku),
        (productID := pt.abi.Uint64()).set(upc.get() + sku.get()),
        (productPrice := pt.abi.Uint64()).set(pt.Int(0)),
        (itemState := pt.abi.String()).set(pt.Bytes("Harvested")),
        (it := Item()).set(sku,
                           upc,
                           farmerAddress,
                           farmerAddress,
                           farmName,
                           farmInformation,
                           farmLongitude,
                           farmLatitude,
                           productID,
                           productNotes,
                           productPrice,
                           itemState,
                           zeroAddress,
                           zeroAddress,
                           zeroAddress),
        supply_chain_app.state.items[upc].set(it),
        supply_chain_app.state.sku.set(sku.get() + pt.Int(1)),
        output.set(supply_chain_app.state.sku)
    )
@supply_chain_app.external(authorize=Authorize.only(supply_chain_app.state.farmer))
def process_item(upc: pt.abi.Uint64, *, output:Item) -> pt.Expr:
    return pt.Seq(
        (it:= Item()).decode(
            supply_chain_app.state.items[upc].get()
        ),
        (state:= pt.abi.String()).set(it.itemState),
        pt.Assert(
            state.get() == Bytes("Harvested"),
            comment="Item's status not harvested",
        ),
        (sku:= pt.abi.Uint64()).set(it.sku),
        (upc:= pt.abi.Uint64()).set(it.upc),
        (ownerID:= pt.abi.Address()).set(it.ownerID),
        (farmerID:= pt.abi.Address()).set(it.farmerID),
        (farmName:= pt.abi.String()).set(it.farmName),
        (farmInformation:= pt.abi.String()).set(it.farmInformation),
        (farmLongitude:= pt.abi.String()).set(it.farmLongitude),
        (farmLatitude:= pt.abi.String()).set(it.farmLatitude),
        (productID:= pt.abi.Uint64()).set(it.productID),
        (productNotes:= pt.abi.String()).set(it.productNotes),
        (productPrice:= pt.abi.Uint64()).set(it.productPrice),
        (itemState := pt.abi.String()).set(pt.Bytes("Processed")),
        (distributorID:= pt.abi.Address()).set(it.distributorID),
        (retailerID:= pt.abi.Address()).set(it.retailerID),
        (consumerID:= pt.abi.Address()).set(it.consumerID),
        it.set(sku,
               upc,
               ownerID,
               farmerID,
               farmName,
               farmInformation,
               farmLongitude,
               farmLatitude,
               productID,
               productNotes,
               productPrice,
               itemState,
               distributorID,
               retailerID,
               consumerID),
        supply_chain_app.state.items[upc].set(it),
        supply_chain_app.state.items[upc].store_into(output)
    )

@supply_chain_app.external(authorize=Authorize.only(supply_chain_app.state.farmer))
def pack_item(upc: pt.abi.Uint64, *, output:Item) -> pt.Expr:
    return pt.Seq(
        (it:= Item()).decode(
            supply_chain_app.state.items[upc].get()
        ),
        (state:= pt.abi.String()).set(it.itemState),
        pt.Assert(
            (state.get() == Bytes("Processed")),
            comment="Item's status not processed",
        ),
        (sku:= pt.abi.Uint64()).set(it.sku),
        (upc:= pt.abi.Uint64()).set(it.upc),
        (ownerID:= pt.abi.Address()).set(it.ownerID),
        (farmerID:= pt.abi.Address()).set(it.farmerID),
        (farmName:= pt.abi.String()).set(it.farmName),
        (farmInformation:= pt.abi.String()).set(it.farmInformation),
        (farmLongitude:= pt.abi.String()).set(it.farmLongitude),
        (farmLatitude:= pt.abi.String()).set(it.farmLatitude),
        (productID:= pt.abi.Uint64()).set(it.productID),
        (productNotes:= pt.abi.String()).set(it.productNotes),
        (productPrice:= pt.abi.Uint64()).set(it.productPrice),
        (itemState := pt.abi.String()).set(pt.Bytes("Packed")),
        (distributorID:= pt.abi.Address()).set(it.distributorID),
        (retailerID:= pt.abi.Address()).set(it.retailerID),
        (consumerID:= pt.abi.Address()).set(it.consumerID),
        it.set(sku,
               upc,
               ownerID,
               farmerID,
               farmName,
               farmInformation,
               farmLongitude,
               farmLatitude,
               productID,
               productNotes,
               productPrice,
               itemState,
               distributorID,
               retailerID,
               consumerID),
        supply_chain_app.state.items[upc].set(it),
        supply_chain_app.state.items[upc].store_into(output)
    )

@supply_chain_app.external(authorize=Authorize.only(supply_chain_app.state.farmer))
def sell_item(upc: pt.abi.Uint64, price: pt.abi.Uint64, *, output:Item) -> pt.Expr:
    return pt.Seq(
        (it:= Item()).decode(
            supply_chain_app.state.items[upc].get()
        ),
        (state:= pt.abi.String()).set(it.itemState),
        pt.Assert(
            (state.get() == Bytes("Packed")),
            comment="Item's status not packed",
        ),
        (sku:= pt.abi.Uint64()).set(it.sku),
        (upc:= pt.abi.Uint64()).set(it.upc),
        (ownerID:= pt.abi.Address()).set(it.ownerID),
        (farmerID:= pt.abi.Address()).set(it.farmerID),
        (farmName:= pt.abi.String()).set(it.farmName),
        (farmInformation:= pt.abi.String()).set(it.farmInformation),
        (farmLongitude:= pt.abi.String()).set(it.farmLongitude),
        (farmLatitude:= pt.abi.String()).set(it.farmLatitude),
        (productID:= pt.abi.Uint64()).set(it.productID),
        (productNotes:= pt.abi.String()).set(it.productNotes),
        (productPrice:= pt.abi.Uint64()).set(price),
        (itemState := pt.abi.String()).set(pt.Bytes("For Sale")),
        (distributorID:= pt.abi.Address()).set(it.distributorID),
        (retailerID:= pt.abi.Address()).set(it.retailerID),
        (consumerID:= pt.abi.Address()).set(it.consumerID),
        it.set(sku,
               upc,
               ownerID,
               farmerID,
               farmName,
               farmInformation,
               farmLongitude,
               farmLatitude,
               productID,
               productNotes,
               productPrice,
               itemState,
               distributorID,
               retailerID,
               consumerID),
        supply_chain_app.state.items[upc].set(it),
        supply_chain_app.state.items[upc].store_into(output)
    )

@supply_chain_app.external(authorize=Authorize.only(supply_chain_app.state.distributor))
def buy_item(upc: pt.abi.Uint64, *, output:Item) -> pt.Expr:
    return pt.Seq(
        (it:= Item()).decode(
            supply_chain_app.state.items[upc].get()
        ),
        (state:= pt.abi.String()).set(it.itemState),
        pt.Assert(
            (state.get() == Bytes("For Sale")),
            comment="Item's status not for sale",
        ),
        (sku:= pt.abi.Uint64()).set(it.sku),
        (upc:= pt.abi.Uint64()).set(it.upc),
        (ownerID:= pt.abi.Address()).set(supply_chain_app.state.distributor),
        (farmerID:= pt.abi.Address()).set(it.farmerID),
        (farmName:= pt.abi.String()).set(it.farmName),
        (farmInformation:= pt.abi.String()).set(it.farmInformation),
        (farmLongitude:= pt.abi.String()).set(it.farmLongitude),
        (farmLatitude:= pt.abi.String()).set(it.farmLatitude),
        (productID:= pt.abi.Uint64()).set(it.productID),
        (productNotes:= pt.abi.String()).set(it.productNotes),
        (productPrice:= pt.abi.Uint64()).set(it.productPrice),
        (itemState := pt.abi.String()).set(pt.Bytes("Sold")),
        (distributorID:= pt.abi.Address()).set(supply_chain_app.state.distributor),
        (retailerID:= pt.abi.Address()).set(it.retailerID),
        (consumerID:= pt.abi.Address()).set(it.consumerID),
        it.set(sku,
               upc,
               ownerID,
               farmerID,
               farmName,
               farmInformation,
               farmLongitude,
               farmLatitude,
               productID,
               productNotes,
               productPrice,
               itemState,
               distributorID,
               retailerID,
               consumerID),
        supply_chain_app.state.items[upc].set(it),
        supply_chain_app.state.items[upc].store_into(output)
    )

@supply_chain_app.external(authorize=Authorize.only(supply_chain_app.state.distributor))
def ship_item(upc: pt.abi.Uint64, *, output:Item) -> pt.Expr:
    return pt.Seq(
        (it:= Item()).decode(
            supply_chain_app.state.items[upc].get()
        ),
        (state:= pt.abi.String()).set(it.itemState),
        pt.Assert(
            (state.get() == Bytes("Sold")),
            comment="Item's status not sold",
        ),
        (sku:= pt.abi.Uint64()).set(it.sku),
        (upc:= pt.abi.Uint64()).set(it.upc),
        (ownerID:= pt.abi.Address()).set(it.ownerID),
        (farmerID:= pt.abi.Address()).set(it.farmerID),
        (farmName:= pt.abi.String()).set(it.farmName),
        (farmInformation:= pt.abi.String()).set(it.farmInformation),
        (farmLongitude:= pt.abi.String()).set(it.farmLongitude),
        (farmLatitude:= pt.abi.String()).set(it.farmLatitude),
        (productID:= pt.abi.Uint64()).set(it.productID),
        (productNotes:= pt.abi.String()).set(it.productNotes),
        (productPrice:= pt.abi.Uint64()).set(it.productPrice),
        (itemState := pt.abi.String()).set(pt.Bytes("Shipped")),
        (distributorID:= pt.abi.Address()).set(it.distributorID),
        (retailerID:= pt.abi.Address()).set(it.retailerID),
        (consumerID:= pt.abi.Address()).set(it.consumerID),
        it.set(sku,
               upc,
               ownerID,
               farmerID,
               farmName,
               farmInformation,
               farmLongitude,
               farmLatitude,
               productID,
               productNotes,
               productPrice,
               itemState,
               distributorID,
               retailerID,
               consumerID),
        supply_chain_app.state.items[upc].set(it),
        supply_chain_app.state.items[upc].store_into(output)
    )

@supply_chain_app.external(authorize=Authorize.only(supply_chain_app.state.retailer))
def receive_item(upc: pt.abi.Uint64, *, output:Item) -> pt.Expr:
    return pt.Seq(
        (it:= Item()).decode(
            supply_chain_app.state.items[upc].get()
        ),
        (state:= pt.abi.String()).set(it.itemState),
        pt.Assert(
            (state.get() == Bytes("Shipped")),
            comment="Item's status not shipped",
        ),
        (sku:= pt.abi.Uint64()).set(it.sku),
        (upc:= pt.abi.Uint64()).set(it.upc),
        (ownerID:= pt.abi.Address()).set(supply_chain_app.state.retailer),
        (farmerID:= pt.abi.Address()).set(it.farmerID),
        (farmName:= pt.abi.String()).set(it.farmName),
        (farmInformation:= pt.abi.String()).set(it.farmInformation),
        (farmLongitude:= pt.abi.String()).set(it.farmLongitude),
        (farmLatitude:= pt.abi.String()).set(it.farmLatitude),
        (productID:= pt.abi.Uint64()).set(it.productID),
        (productNotes:= pt.abi.String()).set(it.productNotes),
        (productPrice:= pt.abi.Uint64()).set(it.productPrice),
        (itemState := pt.abi.String()).set(pt.Bytes("Received")),
        (distributorID:= pt.abi.Address()).set(it.distributorID),
        (retailerID:= pt.abi.Address()).set(supply_chain_app.state.retailer),
        (consumerID:= pt.abi.Address()).set(it.consumerID),
        it.set(sku,
               upc,
               ownerID,
               farmerID,
               farmName,
               farmInformation,
               farmLongitude,
               farmLatitude,
               productID,
               productNotes,
               productPrice,
               itemState,
               distributorID,
               retailerID,
               consumerID),
        supply_chain_app.state.items[upc].set(it),
        supply_chain_app.state.items[upc].store_into(output)
    )

@supply_chain_app.external(authorize=Authorize.only(supply_chain_app.state.consumer))
def purchase_item(upc: pt.abi.Uint64, *, output:Item) -> pt.Expr:
    return pt.Seq(
        (it:= Item()).decode(
            supply_chain_app.state.items[upc].get()
        ),
        (state:= pt.abi.String()).set(it.itemState),
        pt.Assert(
            (state.get() == Bytes("Received")),
            comment="Item's status not received",
        ),
        (sku:= pt.abi.Uint64()).set(it.sku),
        (upc:= pt.abi.Uint64()).set(it.upc),
        (ownerID:= pt.abi.Address()).set(supply_chain_app.state.consumer),
        (farmerID:= pt.abi.Address()).set(it.farmerID),
        (farmName:= pt.abi.String()).set(it.farmName),
        (farmInformation:= pt.abi.String()).set(it.farmInformation),
        (farmLongitude:= pt.abi.String()).set(it.farmLongitude),
        (farmLatitude:= pt.abi.String()).set(it.farmLatitude),
        (productID:= pt.abi.Uint64()).set(it.productID),
        (productNotes:= pt.abi.String()).set(it.productNotes),
        (productPrice:= pt.abi.Uint64()).set(it.productPrice),
        (itemState := pt.abi.String()).set(pt.Bytes("Purchased")),
        (distributorID:= pt.abi.Address()).set(it.distributorID),
        (retailerID:= pt.abi.Address()).set(it.retailerID),
        (consumerID:= pt.abi.Address()).set(supply_chain_app.state.consumer),
        it.set(sku,
               upc,
               ownerID,
               farmerID,
               farmName,
               farmInformation,
               farmLongitude,
               farmLatitude,
               productID,
               productNotes,
               productPrice,
               itemState,
               distributorID,
               retailerID,
               consumerID),
        supply_chain_app.state.items[upc].set(it),
        supply_chain_app.state.items[upc].store_into(output)
    )
    


def demo() -> None:
    # Here we use `sandbox` but beaker.client.api_providers can also be used
    # with something like ``AlgoNode(Network.TestNet).algod()``
    algod_client = sandbox.get_algod_client()

    accts = sandbox.get_accounts()

    farmer = accts.pop()

    distributor = accts.pop()
    
    retailer = accts.pop()

    private_key, consumer = account.generate_account()

    consumer_signer = AccountTransactionSigner(private_key)

    print(f"Consumer Account: {consumer}")

    zero_address="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ"

    # Create an Application client containing both an algod client and app
    app_client = client.ApplicationClient(
        client=algod_client, app=supply_chain_app, signer=farmer.signer
    )

    print(f"Farmer signer is {farmer.signer}")

    # Create the application on chain, implicitly sets the app id for the app client
    app_id, app_addr, txid = app_client.create()
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    app_client.fund(1 * consts.algo)

    result = app_client.call(init_roles, upc=1, farmerAddress=farmer.address, distributorAddress=distributor.address, retailerAddress=retailer.address, consumerAddress=consumer)

    # Harvest Item
    harvest_action = app_client.call(harvest_item, upc=1, farmerAddress=farmer.address, farmName="My Farm", farmInformation="No infos", farmLongitude="", farmLatitude="", productNotes="", zeroAddress=zero_address, boxes=[(app_client.app_id, 1)])
    
    # Process Item 
    process_action = app_client.call(process_item, upc=1, boxes=[(app_client.app_id, 1)])

    print(f"Process action result {process_action.return_value}")

    # Pack Item 
    pack_action = app_client.call(pack_item, upc=1, boxes=[(app_client.app_id, 1)])

    print(f"Pack action result {pack_action.return_value}")

    # Sell Item 
    sell_action = app_client.call(sell_item, upc=1, price=20, boxes=[(app_client.app_id, 1)])

    print(f"Sell action result {sell_action.return_value}")

    distributor_client = app_client.prepare(signer=distributor.signer)
    
    # Buy Item
    buy_action = distributor_client.call(buy_item, upc=1, boxes=[(app_client.app_id, 1)])

    print(f"Distributor action result {buy_action.return_value}")

    # Ship Item
    ship_action = distributor_client.call(ship_item, upc=1, boxes=[(app_client.app_id, 1)])

    print(f"Ship action result {ship_action.return_value}")

    retailer_client = distributor_client.prepare(signer=retailer.signer)

    # Receive Item
    receive_action = retailer_client.call(receive_item, upc=1, boxes=[(app_client.app_id, 1)])

    print(f"Receive action result {receive_action.return_value}")

    retailer_client.fund(1 * consts.algo, consumer)

    consumer_client = retailer_client.prepare(signer=consumer_signer)

    # Purchase Item
    purchase_action = consumer_client.call(purchase_item, upc=1, boxes=[(app_client.app_id, 1)])

    print(f"Purchase action result {purchase_action.return_value}")


if __name__ == "__main__":
    demo()